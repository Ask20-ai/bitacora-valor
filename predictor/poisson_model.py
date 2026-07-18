"""
Modelo Dixon-Coles (Poisson bivariado con corrección para marcadores bajos).

Referencia: Dixon, M.J. and Coles, S.G. (1997), "Modelling Association
Football Scores and Inefficiencies in the Football Betting Market".

Idea general:
- A cada equipo se le asigna una fuerza de ataque y una de defensa.
- Con eso se calcula cuántos goles se espera que meta cada equipo en un
  partido dado (lambda_local, lambda_visitante).
- Se arma la matriz de probabilidad de todos los marcadores posibles usando
  Poisson, con una corrección (rho) para los marcadores bajos (0-0, 1-0,
  0-1, 1-1), que es donde el Poisson puro se aleja más de la realidad.
- Los partidos más recientes pesan más que los viejos (decaimiento temporal).
"""
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from datetime import datetime

# Decaimiento temporal: cuánto "pesa" un partido según su antigüedad en días.
# Con XI=0.0018, un partido de hace 1 año pesa aprox. la mitad que uno de hoy.
XI = 0.0018
RHO_BOUNDS = (-0.2, 0.2)
MAX_GOALS = 8  # tope de goles considerado al armar la matriz de marcadores


def _tau(x: int, y: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Corrección de Dixon-Coles para marcadores bajos."""
    if x == 0 and y == 0:
        return 1 - lam_home * lam_away * rho
    elif x == 0 and y == 1:
        return 1 + lam_home * rho
    elif x == 1 and y == 0:
        return 1 + lam_away * rho
    elif x == 1 and y == 1:
        return 1 - rho
    return 1.0


def fit_dixon_coles(results: list, reference_date: str = None) -> dict:
    """
    results: lista de dicts con home_team, away_team, home_goals, away_goals, date (YYYY-MM-DD).
    Devuelve un dict serializable con las fuerzas de cada equipo y los
    parámetros globales del modelo (home_adv, rho).
    """
    if len(results) < 20:
        raise ValueError(
            f"Muy pocos partidos históricos ({len(results)}) para ajustar el modelo "
            "de forma confiable. Hacen falta al menos ~20-30 partidos por liga."
        )

    teams = sorted({r["home_team"] for r in results} | {r["away_team"] for r in results})
    team_idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    ref_date = datetime.fromisoformat(reference_date) if reference_date else datetime.utcnow()

    home_idx = np.array([team_idx[r["home_team"]] for r in results])
    away_idx = np.array([team_idx[r["away_team"]] for r in results])
    home_goals = np.array([r["home_goals"] for r in results], dtype=float)
    away_goals = np.array([r["away_goals"] for r in results], dtype=float)
    days_ago = np.array([(ref_date - datetime.fromisoformat(r["date"])).days for r in results])
    weights = np.exp(-XI * np.clip(days_ago, 0, None))

    def unpack(params):
        attack = params[:n]
        defense = params[n:2 * n]
        home_adv = params[2 * n]
        rho = params[2 * n + 1]
        return attack, defense, home_adv, rho

    def neg_log_likelihood(params):
        attack, defense, home_adv, rho = unpack(params)
        lam_home = np.exp(home_adv + attack[home_idx] - defense[away_idx])
        lam_away = np.exp(attack[away_idx] - defense[home_idx])

        ll = poisson.logpmf(home_goals, lam_home) + poisson.logpmf(away_goals, lam_away)

        tau_vals = np.array([
            _tau(int(home_goals[i]), int(away_goals[i]), lam_home[i], lam_away[i], rho)
            for i in range(len(results))
        ])
        tau_vals = np.clip(tau_vals, 1e-10, None)

        return -np.sum(weights * (ll + np.log(tau_vals)))

    x0 = np.zeros(2 * n + 2)
    x0[2 * n] = 0.2  # valor inicial razonable para la ventaja de local
    bounds = [(-3, 3)] * n + [(-3, 3)] * n + [(-1, 1)] + [RHO_BOUNDS]

    result = minimize(neg_log_likelihood, x0, method="L-BFGS-B", bounds=bounds)
    attack, defense, home_adv, rho = unpack(result.x)

    return {
        "teams": teams,
        "attack": {t: float(attack[i]) for t, i in team_idx.items()},
        "defense": {t: float(defense[i]) for t, i in team_idx.items()},
        "home_adv": float(home_adv),
        "rho": float(rho),
        "converged": bool(result.success),
        "n_matches": len(results),
        "fitted_at": datetime.utcnow().isoformat(),
    }


def predict_match(model: dict, home_team: str, away_team: str) -> dict:
    """
    Devuelve probabilidades de 1X2 y los marcadores más probables para un
    partido, usando un modelo ya ajustado con fit_dixon_coles.
    """
    attack = model["attack"]
    defense = model["defense"]

    if home_team not in attack or away_team not in attack:
        return None

    home_adv = model["home_adv"]
    rho = model["rho"]

    lam_home = float(np.exp(home_adv + attack[home_team] - defense[away_team]))
    lam_away = float(np.exp(attack[away_team] - defense[home_team]))

    score_probs = {}
    for x in range(MAX_GOALS + 1):
        for y in range(MAX_GOALS + 1):
            p = poisson.pmf(x, lam_home) * poisson.pmf(y, lam_away) * _tau(x, y, lam_home, lam_away, rho)
            score_probs[(x, y)] = max(p, 0.0)

    total = sum(score_probs.values())
    if total <= 0:
        return None
    score_probs = {k: v / total for k, v in score_probs.items()}

    home_win = float(sum(p for (x, y), p in score_probs.items() if x > y))
    draw = float(sum(p for (x, y), p in score_probs.items() if x == y))
    away_win = float(sum(p for (x, y), p in score_probs.items() if x < y))

    top_scores = sorted(score_probs.items(), key=lambda kv: -kv[1])[:5]

    return {
        "lambda_home": round(lam_home, 2),
        "lambda_away": round(lam_away, 2),
        "outcome_probs": {
            "home_win": round(home_win, 4),
            "draw": round(draw, 4),
            "away_win": round(away_win, 4),
        },
        "top_scores": [
            {"score": f"{x}-{y}", "prob": round(float(p), 4)} for (x, y), p in top_scores
        ],
    }
