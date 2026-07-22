import os
import json
from datetime import datetime, timezone

from line_tracker.config import SPORTS, MARKETS, REGION, MONTHLY_CREDIT_BUDGET, \
    SPREAD_MOVE_THRESHOLD, MONEYLINE_MOVE_THRESHOLD, TOTAL_MOVE_THRESHOLD
from line_tracker.odds_client import OddsApiClient, MonthlyBudgetExceeded
from line_tracker.snapshot_store import update_snapshots
from line_tracker.movement_detector import detect_movements

THRESHOLDS = {
    "spread": SPREAD_MOVE_THRESHOLD,
    "moneyline": MONEYLINE_MOVE_THRESHOLD,
    "total": TOTAL_MOVE_THRESHOLD,
}

RESULTS_FILE = "line_tracker/data/movements.json"


def _ensure_data_folder():
    os.makedirs("line_tracker/data/snapshots", exist_ok=True)
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"generated_at": None, "movements": []}, f)


def main():
    _ensure_data_folder()
    api_key = os.environ.get("ODDS_API_KEY")
    client = OddsApiClient(api_key, MONTHLY_CREDIT_BUDGET)

    all_movements = []

    for sport in SPORTS:
        try:
            games = client.get_odds(sport["key"], MARKETS, REGION)
        except MonthlyBudgetExceeded as e:
            print(f"[STOP] {e}")
            break
        except Exception as e:
            print(f"[ERROR] '{sport['label']}': {e}")
            continue

        if not games:
            print(f"[INFO] '{sport['label']}': sin partidos próximos con cuotas disponibles "
                  "(probablemente fuera de temporada).")
            continue

        games_with_history = update_snapshots(sport["key"], games)
        movements = detect_movements(games_with_history, THRESHOLDS)

        for m in movements:
            m["sport"] = sport["label"]
        all_movements.extend(movements)

        print(f"[INFO] '{sport['label']}': {len(games)} partidos revisados, "
              f"{len(movements)} con movimiento significativo.")

    print(f"\nTotal movimientos detectados: {len(all_movements)}")
    print(f"Créditos usados este mes: {client.credits_used_this_month}/{MONTHLY_CREDIT_BUDGET}")

    os.makedirs("line_tracker/data", exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "movements": all_movements,
        }, f, indent=2, ensure_ascii=False)

    print(f"Resultados guardados en {RESULTS_FILE}")


if __name__ == "__main__":
    main()
