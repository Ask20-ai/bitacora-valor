"""
Script de PRUEBA para validar el ajuste del modelo con datos reales de MLS,
usando Highlightly (mismo proveedor que ya usa el resto del sistema).

Se corre vÃ­a el workflow manual '.github/workflows/predictor_test.yml'.
"""
import os
import json
from datetime import datetime

from api_client import HighlightlyClient
from leagues_store import resolve_leagues
from predictor.results_store import update_results
from predictor.poisson_model import fit_dixon_coles, predict_match

MAX_REQUESTS = 20  # de sobra para esta prueba (1 liga, pocas temporadas)
LEAGUE_KEY = "mls"
LEAGUE_CONFIG = [{"key": LEAGUE_KEY, "search": "MLS", "country": "USA"}]


def _ensure_predictor_folders():
    """
    Crea predictor/data/results y predictor/data/models con un placeholder
    desde el arranque, para que 'git add predictor/data/' nunca falle (git no
    trackea carpetas vacÃ­as) aunque el script corte antes de tiempo.
    """
    for folder in ("predictor/data/results", "predictor/data/models"):
        os.makedirs(folder, exist_ok=True)
        placeholder = os.path.join(folder, ".gitkeep")
        if not os.listdir(folder):
            open(placeholder, "w").close()


def main():
    _ensure_predictor_folders()

    api_key = os.environ.get("HIGHLIGHTLY_API_KEY")
    client = HighlightlyClient(api_key, MAX_REQUESTS)

    print("Buscando liga MLS (reusando el resolver que ya usa el resto del sistema)...")
    leagues = resolve_leagues(client, LEAGUE_CONFIG)
    league = leagues.get(LEAGUE_KEY)
    if not league:
        print("[ERROR] No se pudo resolver la liga MLS. Abortando.")
        return

    league_id = league["id"]
    latest_season = league.get("latest_season")
    print(f"Liga: {league['name']} (id={league_id}), temporada mÃ¡s reciente conocida: {latest_season}")

    if latest_season is None:
        print("[ERROR] No hay temporada disponible para esta liga.")
        return

    # Probamos la temporada mÃ¡s reciente y hasta 2 hacia atrÃ¡s (3 en total)
    seasons_to_use = [latest_season, latest_season - 1, latest_season - 2]

    all_results = update_results(client, LEAGUE_KEY, league_id, seasons_to_use)
    print(f"\nTotal de partidos en el historial: {len(all_results)}")
    print(f"Requests usados: {client.requests_used}/{MAX_REQUESTS}")

    if len(all_results) < 20:
        print("\n[AVISO] Muy pocos partidos para ajustar el modelo de forma confiable todavÃ­a.")
        return

    print("\nAjustando el modelo Dixon-Coles (puede tardar unos segundos)...")
    model = fit_dixon_coles(all_results)

    print(f"Â¿ConvergiÃ³?: {model['converged']}")
    print(f"Ventaja de local (home_adv): {model['home_adv']:.3f}")
    print(f"Rho (correcciÃ³n marcadores bajos): {model['rho']:.3f}")
    print(f"Partidos usados en el ajuste: {model['n_matches']}")

    os.makedirs("predictor/data/models", exist_ok=True)
    with open(f"predictor/data/models/{LEAGUE_KEY}.json", "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    print("\nTop 8 equipos por fuerza de ataque:")
    ranking = sorted(model["attack"].items(), key=lambda kv: -kv[1])[:8]
    for team, val in ranking:
        print(f"  {team}: {val:.2f} (defensa: {model['defense'][team]:.2f})")

    last_match = all_results[-1]
    home, away = last_match["home_team"], last_match["away_team"]
    real_score = f"{last_match['home_goals']}-{last_match['away_goals']}"

    print(f"\nPredicciÃ³n de ejemplo: {home} (local) vs {away} (visitante)")
    print(f"(Resultado real de ese partido en el historial: {real_score})")

    pred = predict_match(model, home, away)
    if pred:
        print(f"  Goles esperados: {pred['lambda_home']} - {pred['lambda_away']}")
        o = pred["outcome_probs"]
        print(f"  1X2 -> Local: {o['home_win']*100:.1f}% | Empate: {o['draw']*100:.1f}% | Visitante: {o['away_win']*100:.1f}%")
        print("  Marcadores mÃ¡s probables:")
        for s in pred["top_scores"]:
            print(f"    {s['score']}: {s['prob']*100:.1f}%")
    else:
        print("  No se pudo predecir (Â¿nombres de equipo no coinciden?)")

    print("\n=== FIN DE LA PRUEBA ===")


if __name__ == "__main__":
    main()
