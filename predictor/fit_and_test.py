"""
Script de PRUEBA para validar el ajuste del modelo con datos reales de MLS
antes de integrarlo al resto del sistema.

Se corre vía el workflow manual '.github/workflows/predictor_test.yml',
o localmente con la variable de entorno API_FOOTBALL_KEY seteada.
"""
import os
import json

from predictor.af_client import ApiFootballClient
from predictor.results_store import update_results
from predictor.poisson_model import fit_dixon_coles, predict_match

MAX_REQUESTS = 20  # de sobra para esta prueba (1 liga, 2 temporadas)
LEAGUE_KEY = "mls"
LEAGUE_SEARCH = "MLS"
LEAGUE_COUNTRY = "USA"


def main():
    api_key = os.environ.get("API_FOOTBALL_KEY")
    client = ApiFootballClient(api_key, MAX_REQUESTS)

    print(f"Buscando liga '{LEAGUE_SEARCH}'...")
    results = client.search_league(LEAGUE_SEARCH, LEAGUE_COUNTRY)
    if not results:
        print("[ERROR] No se encontró la liga. Abortando.")
        return

    league = results[0]
    league_id = league["league"]["id"]
    league_name = league["league"]["name"]
    seasons_available = sorted(s["year"] for s in league.get("seasons", []))

    if not seasons_available:
        print("[ERROR] La liga no tiene temporadas listadas en la API.")
        return

    latest_season = seasons_available[-1]
    # Probamos hasta 5 temporadas hacia atrás (de la más reciente a la más
    # vieja). Si tu plan actual restringe algunas (ej. solo te deja ver
    # temporadas viejas), esas se saltan solas sin romper el resto —
    # ver el manejo de errores en update_results().
    seasons_to_use = sorted(seasons_available, reverse=True)[:5]

    print(f"Liga encontrada: {league_name} (id={league_id})")
    print(f"Temporadas disponibles: {seasons_available}")
    print(f"Usando: {seasons_to_use}")

    all_results = update_results(client, LEAGUE_KEY, league_id, seasons_to_use)
    print(f"\nTotal de partidos en el historial: {len(all_results)}")
    print(f"Requests usados: {client.requests_used}/{MAX_REQUESTS}")

    if len(all_results) < 20:
        print("\n[AVISO] Muy pocos partidos para ajustar el modelo de forma confiable todavía.")
        return

    print("\nAjustando el modelo Dixon-Coles (puede tardar unos segundos)...")
    model = fit_dixon_coles(all_results)

    print(f"¿Convergió?: {model['converged']}")
    print(f"Ventaja de local (home_adv): {model['home_adv']:.3f}")
    print(f"Rho (corrección marcadores bajos): {model['rho']:.3f}")
    print(f"Partidos usados en el ajuste: {model['n_matches']}")

    os.makedirs("predictor/data/models", exist_ok=True)
    with open(f"predictor/data/models/{LEAGUE_KEY}.json", "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    print("\nTop 8 equipos por fuerza de ataque:")
    ranking = sorted(model["attack"].items(), key=lambda kv: -kv[1])[:8]
    for team, val in ranking:
        print(f"  {team}: {val:.2f} (defensa: {model['defense'][team]:.2f})")

    # Prueba de predicción con el último partido real del historial
    last_match = all_results[-1]
    home, away = last_match["home_team"], last_match["away_team"]
    real_score = f"{last_match['home_goals']}-{last_match['away_goals']}"

    print(f"\nPredicción de ejemplo: {home} (local) vs {away} (visitante)")
    print(f"(Resultado real de ese partido en el historial: {real_score})")

    pred = predict_match(model, home, away)
    if pred:
        print(f"  Goles esperados: {pred['lambda_home']} - {pred['lambda_away']}")
        o = pred["outcome_probs"]
        print(f"  1X2 -> Local: {o['home_win']*100:.1f}% | Empate: {o['draw']*100:.1f}% | Visitante: {o['away_win']*100:.1f}%")
        print("  Marcadores más probables:")
        for s in pred["top_scores"]:
            print(f"    {s['score']}: {s['prob']*100:.1f}%")
    else:
        print("  No se pudo predecir (¿nombres de equipo no coinciden?)")

    print("\n=== FIN DE LA PRUEBA ===")


if __name__ == "__main__":
    main()
