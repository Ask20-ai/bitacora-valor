"""
Guarda un snapshot de las cuotas de cada partido cada vez que corre el
rastreador, para poder comparar contra el snapshot anterior y detectar
movimiento de línea.
"""
import os
import json
from datetime import datetime, timezone

SNAPSHOTS_DIR = "line_tracker/data/snapshots"


def _snapshot_path(sport_key: str) -> str:
    return os.path.join(SNAPSHOTS_DIR, f"{sport_key}.json")


def load_snapshots(sport_key: str) -> dict:
    """Devuelve {game_id: {"history": [...], "meta": {...}}}"""
    path = _snapshot_path(sport_key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_snapshots(sport_key: str, snapshots: dict):
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    with open(_snapshot_path(sport_key), "w", encoding="utf-8") as f:
        json.dump(snapshots, f, indent=2, ensure_ascii=False)


def _extract_main_lines(game: dict) -> dict:
    """
    Saca la línea 'de consenso' (promedio simple entre las casas disponibles)
    para h2h, spread y total, de la respuesta de The Odds API.
    """
    h2h_home, h2h_away = [], []
    spread_home = []
    total_points = []

    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    if outcome["name"] == game["home_team"]:
                        h2h_home.append(outcome["price"])
                    elif outcome["name"] == game["away_team"]:
                        h2h_away.append(outcome["price"])
            elif market["key"] == "spreads":
                for outcome in market["outcomes"]:
                    if outcome["name"] == game["home_team"]:
                        spread_home.append(outcome["point"])
            elif market["key"] == "totals":
                for outcome in market["outcomes"]:
                    if outcome["name"] == "Over":
                        total_points.append(outcome["point"])

    def avg(values):
        return round(sum(values) / len(values), 2) if values else None

    return {
        "h2h_home": avg(h2h_home),
        "h2h_away": avg(h2h_away),
        "spread_home": avg(spread_home),
        "total": avg(total_points),
    }


def update_snapshots(sport_key: str, games: list) -> list:
    """
    Agrega un snapshot nuevo para cada partido próximo, y devuelve la lista de
    partidos con su historial actualizado (para que movement_detector lo procese).
    """
    snapshots = load_snapshots(sport_key)
    now = datetime.now(timezone.utc).isoformat()

    updated = []
    for game in games:
        game_id = game["id"]
        lines = _extract_main_lines(game)

        entry = snapshots.setdefault(game_id, {
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "commence_time": game["commence_time"],
            "history": [],
        })
        entry["history"].append({"at": now, **lines})
        updated.append({"game_id": game_id, **entry})

    save_snapshots(sport_key, snapshots)
    return updated
