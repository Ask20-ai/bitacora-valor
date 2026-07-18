"""
Orquesta el modelo de predicción dentro del flujo principal:
- Reentrena el modelo de cada liga una vez por semana (no hace falta más
  seguido; los ratings de los equipos no cambian de un día para el otro).
- Genera predicciones (1X2 + marcadores más probables) para los partidos
  próximos de cada liga activa.
"""
import os
import json
from datetime import datetime, timedelta, timezone

from predictor.results_store import update_results
from predictor.poisson_model import fit_dixon_coles, predict_match

MODEL_MAX_AGE_DAYS = 7
MODELS_DIR = "predictor/data/models"
SEASONS_BACK = 3  # temporada actual + 2 anteriores


def _model_path(league_key: str) -> str:
    return os.path.join(MODELS_DIR, f"{league_key}.json")


def _load_model_if_fresh(league_key: str):
    path = _model_path(league_key)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        model = json.load(f)
    fitted_at = datetime.fromisoformat(model["fitted_at"])
    if fitted_at.tzinfo is None:
        fitted_at = fitted_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - fitted_at
    if age > timedelta(days=MODEL_MAX_AGE_DAYS):
        return None
    return model


def _save_model(league_key: str, model: dict):
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(_model_path(league_key), "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)


def get_or_refit_model(client, league_key: str, league_id: int, latest_season: int):
    """
    Devuelve un modelo ajustado para la liga, reusando el que ya esté guardado
    si tiene menos de MODEL_MAX_AGE_DAYS, o reentrenando si no.
    """
    model = _load_model_if_fresh(league_key)
    if model is not None:
        return model, False  # False = no se reentrenó esta vez

    print(f"[INFO] '{league_key}': reentrenando el modelo (no había uno, o venció)...")
    seasons = [latest_season - i for i in range(SEASONS_BACK)]
    results = update_results(client, league_key, league_id, seasons)

    if len(results) < 20:
        print(f"[AVISO] '{league_key}': muy pocos partidos históricos ({len(results)}) "
              "para ajustar el modelo todavía.")
        return None, True

    model = fit_dixon_coles(results)
    _save_model(league_key, model)
    return model, True


def generate_predictions(client, leagues: dict, upcoming_by_league: dict) -> list:
    """
    leagues: el mismo dict que devuelve resolve_leagues() (id, name, latest_season por liga)
    upcoming_by_league: {league_key: [fixtures próximos ya filtrados]}
    Devuelve una lista de predicciones listas para el HTML.
    """
    predictions = []

    for league_key, league_info in leagues.items():
        upcoming = upcoming_by_league.get(league_key, [])
        if not upcoming:
            continue

        latest_season = league_info.get("latest_season")
        if latest_season is None:
            continue

        model, _ = get_or_refit_model(client, league_key, league_info["id"], latest_season)
        if model is None:
            continue

        for match in upcoming:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            pred = predict_match(model, home, away)
            if pred is None:
                continue  # equipo nuevo/ascendido sin historial suficiente

            predictions.append({
                "league": league_info["name"],
                "date": match["date"][:16].replace("T", " "),
                "home": home,
                "away": away,
                "prediction": pred,
            })

    return predictions
