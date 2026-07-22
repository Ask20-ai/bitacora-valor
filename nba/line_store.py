"""
Guarda un snapshot del estado de la línea (moneyline) cada vez que corre el
script, por partido y por casa de apuestas, para poder comparar cómo se movió
con el tiempo (esto es lo que necesitamos para detectar steam moves).
"""
import os
import json
from datetime import datetime, timezone

LINES_DIR = "nba/data/lines"


def _decimal_to_prob(price: float) -> float:
    """Convierte cuota decimal a probabilidad implícita. Ej: 2.00 -> 0.50"""
    if not price or price <= 0:
        return None
    return 1 / price


def _game_path(game_id: str) -> str:
    return os.path.join(LINES_DIR, f"{game_id}.json")


def load_history(game_id: str) -> list:
    path = _game_path(game_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(game_id: str, history: list):
    os.makedirs(LINES_DIR, exist_ok=True)
    with open(_game_path(game_id), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def record_snapshot(odds_response: list) -> list:
    """
    odds_response: la lista que devuelve OddsApiClient.get_moneyline_odds().
    Guarda un snapshot nuevo por partido (con el precio de cada casa de
    apuestas) y devuelve la lista de game_ids que se actualizaron.
    """
    now = datetime.now(timezone.utc).isoformat()
    updated_games = []

    for game in odds_response:
        game_id = game.get("id") or game.get("event_id")
        if not game_id:
            continue

        home_team = game.get("home_team")
        away_team = game.get("away_team")

        books_snapshot = []
        for bookmaker in game.get("bookmakers", []):
            h2h_market = next((m for m in bookmaker.get("markets", []) if m.get("key") == "h2h"), None)
            if not h2h_market:
                continue
            outcomes = {o["name"]: o["price"] for o in h2h_market.get("outcomes", [])}
            home_price = outcomes.get(home_team)
            away_price = outcomes.get(away_team)
            books_snapshot.append({
                "bookmaker": bookmaker.get("title", bookmaker.get("key")),
                "home_price": home_price,
                "away_price": away_price,
                "home_prob": _decimal_to_prob(home_price),
                "away_prob": _decimal_to_prob(away_price),
            })

        if not books_snapshot:
            continue

        history = load_history(game_id)
        history.append({
            "timestamp": now,
            "home_team": home_team,
            "away_team": away_team,
            "commence_time": game.get("commence_time"),
            "books": books_snapshot,
        })
        save_history(game_id, history)
        updated_games.append(game_id)

    return updated_games
