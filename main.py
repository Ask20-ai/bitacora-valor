import os
import json
from datetime import datetime, timedelta, timezone

from config import LEAGUES, LOOKAHEAD_DAYS, MAX_REQUESTS_PER_RUN
from api_client import HighlightlyClient, RequestBudgetExceeded, RateLimitExceeded
from leagues_store import resolve_leagues
from analyze import team_rolling_stats, evaluate_market
from render_html import render

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


def main():
    api_key = os.environ.get("HIGHLIGHTLY_API_KEY")
    client = HighlightlyClient(api_key, MAX_REQUESTS_PER_RUN)

    try:
        leagues = resolve_leagues(client, LEAGUES)
    except RateLimitExceeded as e:
        print(f"[STOP] {e}")
        return

    if not leagues:
        print("No hay ligas resueltas. Revisá tu API key y la configuración de LEAGUES.")
        return

    now = datetime.now(timezone.utc)
    date_to = now + timedelta(days=LOOKAHEAD_DAYS)


    all_alerts = []
    stats_cache = {}  # evita recalcular el mismo equipo/mercado dos veces en la misma corrida
    rate_limited = False

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

        if not upcoming:
            print(f"[INFO] '{key}': sin partidos próximos entre hoy y +{LOOKAHEAD_DAYS} días.")
            continue

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

    html = render(all_alerts)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML generado en docs/index.html")


if __name__ == "__main__":
    main()
