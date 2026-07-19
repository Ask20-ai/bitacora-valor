import os
import json
from datetime import datetime, timedelta, timezone

from config import LEAGUES, LOOKAHEAD_DAYS, MAX_REQUESTS_PER_RUN
from api_client import HighlightlyClient, RequestBudgetExceeded, RateLimitExceeded
from leagues_store import resolve_leagues
from analyze import team_rolling_stats, evaluate_market
from render_html import render
from predictor.predict import generate_predictions

MARKETS = ["corners", "cards"]
ALERTS_LOG_FILE = "data/alerts_log.json"


def _is_upcoming(match: dict, date_from: datetime, date_to: datetime) -> bool:
    state_desc = match.get("state", {}).get("description", "")
    if state_desc != "Not started":
        return False
    match_date_str = match.get("date")
    if not match_date_str:
        return False
    try:
        match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
    except ValueError:
        return False
    return date_from <= match_date <= date_to


def _write_status_page(message: str):
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(render([], predictions=[], status_message=message))


def _ensure_folders_with_placeholder():
    """
    Crea data/ y docs/ desde el arranque, con un mensaje de estado, para que
    'git add data/ docs/' nunca falle (git no trackea carpetas vacÃ­as) Y para
    que la pÃ¡gina SIEMPRE refleje la corrida mÃ¡s reciente, aunque falle antes
    de llegar al final (asÃ­ no queda contenido viejo escondiendo un problema).
    """
    os.makedirs("data", exist_ok=True)
    _write_status_page("Corrida en curso...")


def main():
    _ensure_folders_with_placeholder()

    api_key = os.environ.get("HIGHLIGHTLY_API_KEY")
    client = HighlightlyClient(api_key, MAX_REQUESTS_PER_RUN)

    try:
        leagues = resolve_leagues(client, LEAGUES)
    except RateLimitExceeded as e:
        print(f"[STOP] {e}")
        _write_status_page(f"La corrida se detuvo por lÃ­mite de cuota de la API: {e}")
        return

    if not leagues:
        print("No hay ligas resueltas. RevisÃ¡ tu API key y la configuraciÃ³n de LEAGUES.")
        _write_status_page(
            "No se pudo resolver ninguna liga en esta corrida (revisar logs del workflow "
            "en GitHub Actions para mÃ¡s detalle)."
        )
        return

    now = datetime.now(timezone.utc)
    date_to = now + timedelta(days=LOOKAHEAD_DAYS)


    all_alerts = []
    upcoming_by_league = {}
    rate_limited = False

    # Paso 1: solo traer los partidos prÃ³ximos de cada liga (barato, ya con
    # paginaciÃ³n completa). TodavÃ­a no gastamos presupuesto en stats por equipo.
    for key, league_info in leagues.items():
        if rate_limited:
            break

        league_id = league_info["id"]
        season = league_info.get("latest_season")
        if season is None:
            print(f"[AVISO] '{key}': no se pudo determinar la temporada, se salta esta liga.")
            continue

        try:
            response = client.matches_by_league_season(league_id, season)
        except RateLimitExceeded as e:
            print(f"[STOP] {e}")
            rate_limited = True
            break
        except RequestBudgetExceeded as e:
            print(f"[STOP] {e}")
            break
        except Exception as e:
            print(f"[ERROR] Partidos de '{key}': {e}")
            continue

        matches = response.get("data", [])
        upcoming = [m for m in matches if _is_upcoming(m, now, date_to)]
        upcoming_by_league[key] = upcoming

        if not upcoming:
            print(f"[INFO] '{key}': sin partidos prÃ³ximos entre hoy y +{LOOKAHEAD_DAYS} dÃ­as.")

    # Paso 2: generar predicciones ANTES que las alertas. El entrenamiento del
    # modelo es un gasto de una sola vez (despuÃ©s queda cacheado ~7 dÃ­as), asÃ­
    # que lo priorizamos para que nunca compita por presupuesto contra el
    # anÃ¡lisis de corners/tarjetas, que puede seguir corriendo todos los dÃ­as.
    all_predictions = []
    if not rate_limited:
        try:
            all_predictions = generate_predictions(client, leagues, upcoming_by_league)
            print(f"Total predicciones generadas: {len(all_predictions)}")
        except RateLimitExceeded as e:
            print(f"[STOP] Predicciones cortadas por lÃ­mite de cuota: {e}")
            rate_limited = True
        except Exception as e:
            print(f"[ERROR] Generando predicciones: {e}")
    else:
        print("Se salteÃ³ la generaciÃ³n de predicciones (ya se habÃ­a alcanzado el lÃ­mite de cuota).")

    # Paso 3: alertas de corners/tarjetas, con el presupuesto que quede.
    stats_cache = {}  # evita recalcular el mismo equipo/mercado dos veces en la misma corrida

    for key, upcoming in upcoming_by_league.items():
        if rate_limited:
            break
        league_info = leagues[key]

        for match in upcoming:
            if rate_limited:
                break

            home = match["homeTeam"]
            away = match["awayTeam"]
            fixture_meta = {
                "league": league_info["name"],
                "date": match["date"][:16].replace("T", " "),
                "home": home["name"],
                "away": away["name"],
            }

            for market in MARKETS:
                try:
                    if (home["id"], market) not in stats_cache:
                        stats_cache[(home["id"], market)] = team_rolling_stats(client, home["id"], market)
                    if (away["id"], market) not in stats_cache:
                        stats_cache[(away["id"], market)] = team_rolling_stats(client, away["id"], market)

                    home_stats = stats_cache[(home["id"], market)]
                    away_stats = stats_cache[(away["id"], market)]

                    result = evaluate_market(home_stats, away_stats, market)
                    if result:
                        all_alerts.append({"fixture": fixture_meta, "result": result})

                except RateLimitExceeded as e:
                    print(f"[STOP] {e}")
                    rate_limited = True
                    break
                except RequestBudgetExceeded as e:
                    print(f"[STOP] {e}")
                    break
                except Exception as e:
                    print(f"[ERROR] Analizando {fixture_meta['home']} vs {fixture_meta['away']} ({market}): {e}")
                    continue

    print(f"\nTotal alertas encontradas: {len(all_alerts)}")
    print(f"Requests usados en esta corrida: {client.requests_used}/{MAX_REQUESTS_PER_RUN}")

    os.makedirs("data", exist_ok=True)
    log = []
    if os.path.exists(ALERTS_LOG_FILE):
        with open(ALERTS_LOG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    log.append({
        "run_at": datetime.now(timezone.utc).isoformat(),
        "alerts": all_alerts,
    })
    with open(ALERTS_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    html = render(all_alerts, predictions=all_predictions)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML generado en docs/index.html")


if __name__ == "__main__":
    main()
