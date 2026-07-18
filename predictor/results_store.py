"""
Mantiene un archivo por liga con el historial de resultados (goles local/visita,
fecha, equipos) que alimenta el modelo Dixon-Coles.

Usa el mismo cliente de Highlightly (api_client.py) que ya usa el resto del
sistema para corners/tarjetas — no hace falta ninguna API nueva. El marcador
final viene en el propio endpoint /matches, en state.score.current
(ej. "5 - 0"), cuando state.description == "Finished".
"""
import os
import json

RESULTS_DIR = "predictor/data/results"


def _results_path(league_key: str) -> str:
    return os.path.join(RESULTS_DIR, f"{league_key}.json")


def load_results(league_key: str) -> list:
    path = _results_path(league_key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_results(league_key: str, results: list):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(_results_path(league_key), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def _parse_score(score_current: str):
    """'5 - 0' -> (5, 0). Devuelve None si el formato no es el esperado."""
    if not score_current:
        return None
    parts = score_current.split(" - ")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        return None


def _to_record(match: dict):
    state = match.get("state", {})
    if state.get("description") != "Finished":
        return None

    score = _parse_score(state.get("score", {}).get("current"))
    if score is None:
        return None
    home_goals, away_goals = score

    return {
        "match_id": match["id"],
        "date": match["date"][:10],
        "home_team": match["homeTeam"]["name"],
        "away_team": match["awayTeam"]["name"],
        "home_goals": home_goals,
        "away_goals": away_goals,
    }


def update_results(client, league_key: str, league_id: int, seasons: list) -> list:
    """
    Trae los partidos finalizados de las temporadas indicadas (vía Highlightly)
    y los combina con lo que ya había guardado, sin duplicar (por match_id).
    Las temporadas que el plan actual no deje ver simplemente devuelven poco
    o nada, sin romper el resto.
    """
    existing = load_results(league_key)
    existing_ids = {r["match_id"] for r in existing}

    new_records = []
    for season in seasons:
        try:
            response = client.matches_by_league_season(league_id, season, permanent=True)
        except Exception as e:
            print(f"[AVISO] No se pudo traer la temporada {season} de '{league_key}': {e}")
            continue

        matches = response.get("data", [])
        for match in matches:
            record = _to_record(match)
            if record and record["match_id"] not in existing_ids:
                new_records.append(record)
                existing_ids.add(record["match_id"])

    combined = existing + new_records
    combined.sort(key=lambda r: r["date"])
    save_results(league_key, combined)
    print(f"[INFO] '{league_key}': {len(new_records)} partidos nuevos agregados "
          f"(total histórico: {len(combined)})")
    return combined
