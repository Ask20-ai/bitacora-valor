"""
Mantiene un archivo por liga con el historial de resultados (goles local/visita,
fecha, equipos) que alimenta el modelo Dixon-Coles.

Partidos ya finalizados no cambian, así que esto se guarda para siempre y en
cada corrida solo se agregan los partidos finalizados que todavía no estén
en el archivo (por eso el consumo de requests baja con el tiempo, salvo la
temporada en curso que sigue sumando fechas).
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


def _to_record(fixture: dict) -> dict:
    return {
        "fixture_id": fixture["fixture"]["id"],
        "date": fixture["fixture"]["date"][:10],
        "home_team": fixture["teams"]["home"]["name"],
        "away_team": fixture["teams"]["away"]["name"],
        "home_goals": fixture["goals"]["home"],
        "away_goals": fixture["goals"]["away"],
    }


def update_results(client, league_key: str, league_id: int, seasons: list) -> list:
    """
    Trae los partidos finalizados de las temporadas indicadas y los combina
    con lo que ya había guardado, sin duplicar (por fixture_id).
    """
    existing = load_results(league_key)
    existing_ids = {r["fixture_id"] for r in existing}

    new_records = []
    for season in seasons:
        try:
            fixtures = client.finished_fixtures(league_id, season)
        except Exception as e:
            print(f"[AVISO] No se pudo traer la temporada {season} de '{league_key}' "
                  f"(probablemente restringida por tu plan actual): {e}")
            continue
        for fx in fixtures:
            record = _to_record(fx)
            if record["fixture_id"] not in existing_ids:
                new_records.append(record)
                existing_ids.add(record["fixture_id"])

    combined = existing + new_records
    combined.sort(key=lambda r: r["date"])
    save_results(league_key, combined)
    print(f"[INFO] '{league_key}': {len(new_records)} partidos nuevos agregados "
          f"(total histórico: {len(combined)})")
    return combined
