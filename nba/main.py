import os
import json
from datetime import datetime, timezone

from nba.odds_client import OddsApiClient, RequestBudgetExceeded
from nba.line_store import record_snapshot, load_history, LINES_DIR
from nba.steam_detector import detect_steam_move
from nba.render_nba import render_nba

MAX_HISTORY_PER_GAME = 100  # tope de snapshots guardados por partido, para no crecer sin límite


def _trim_history():
    if not os.path.exists(LINES_DIR):
        return
    for filename in os.listdir(LINES_DIR):
        path = os.path.join(LINES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
        if len(history) > MAX_HISTORY_PER_GAME:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history[-MAX_HISTORY_PER_GAME:], f, indent=2, ensure_ascii=False)


def main():
    os.makedirs("nba/data/lines", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    # Placeholder inmediato: por si el script corta antes de tiempo, docs/nba.html
    # siempre tiene contenido fresco (mismo criterio que main.py del lado de fútbol).
    with open("docs/nba.html", "w", encoding="utf-8") as f:
        f.write(render_nba([]))

    api_key = os.environ.get("THE_ODDS_API_KEY")
    client = OddsApiClient(api_key, max_requests=5)

    try:
        odds_response = client.get_moneyline_odds("basketball_nba")
    except RequestBudgetExceeded as e:
        print(f"[STOP] {e}")
        return
    except Exception as e:
        print(f"[ERROR] No se pudo traer las odds de NBA: {e}")
        return

    updated_games = record_snapshot(odds_response)
    print(f"Snapshots actualizados: {len(updated_games)} partidos")

    steam_alerts = []
    for game_id in updated_games:
        history = load_history(game_id)
        alert = detect_steam_move(history)
        if alert:
            steam_alerts.append(alert)

    print(f"Steam moves detectados: {len(steam_alerts)}")
    print(f"Requests usados: {client.requests_used}/{client.max_requests}")

    _trim_history()

    html = render_nba(steam_alerts)
    with open("docs/nba.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML generado en docs/nba.html")


if __name__ == "__main__":
    main()
