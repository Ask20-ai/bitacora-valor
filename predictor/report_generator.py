"""
Arma un informe en texto por partido, combinando:
- Las probabilidades del modelo Dixon-Coles (1X2 + marcador más probable)
- Las alertas de corners/tarjetas (doble confirmación ataque/defensa)

Es texto generado con reglas a partir de los números ya calculados — no es
una IA "adivinando" el partido. Todo lo que dice el informe es trazable a un
cálculo concreto hecho antes en el pipeline.
"""

MARKET_LABELS = {"corners": "corners", "cards": "tarjetas"}


def _fixture_key(fixture: dict) -> tuple:
    return (fixture["league"], fixture["date"], fixture["home"], fixture["away"])


def _describe_outcome(pred: dict, home: str, away: str) -> str:
    o = pred["outcome_probs"]
    home_pct, draw_pct, away_pct = o["home_win"] * 100, o["draw"] * 100, o["away_win"] * 100
    favorite, fav_pct = max([(home, home_pct), ("empate", draw_pct), (away, away_pct)], key=lambda t: t[1])

    if fav_pct >= 55:
        strength = f"{favorite} aparece como favorito claro ({fav_pct:.0f}%)"
    elif fav_pct >= 40:
        strength = f"{favorite} es el resultado más probable, pero sin ser un partido cerrado ({fav_pct:.0f}%)"
    else:
        strength = "es un partido muy parejo, sin un favorito definido"

    top = pred["top_scores"][0]
    return (
        f"Según el modelo, {strength}. Se esperan {pred['lambda_home']} goles de {home} "
        f"y {pred['lambda_away']} de {away}; el marcador más probable es {top['score']} "
        f"({top['prob']*100:.0f}%)."
    )


def _describe_alert(alert_result: dict, home: str, away: str) -> str:
    market_label = MARKET_LABELS.get(alert_result["market"], alert_result["market"])
    line = alert_result["line_reference"]
    total = alert_result["projected_total"]
    margin = total - line
    sides = " y ".join(s["side"] for s in alert_result["signals"])

    if margin >= 2:
        strength = "con bastante margen"
    elif margin >= 0.5:
        strength = "por encima"
    else:
        strength = "apenas por encima"

    return (
        f"En {market_label}, hay doble confirmación del lado de {sides}: la proyección combinada "
        f"({total}) queda {strength} de la línea de referencia ({line})."
    )


def _confidence_score(alert_result: dict) -> float:
    """Qué tan por encima de la línea está la proyección, en proporción — para rankear cuál alerta es más fuerte."""
    return (alert_result["projected_total"] - alert_result["line_reference"]) / alert_result["line_reference"]


def build_match_reports(alerts: list, predictions: list) -> list:
    """
    Agrupa alertas y predicciones por partido, y arma un texto narrativo por
    cada uno. Devuelve una lista de {fixture, narrative, best_bet}.
    """
    grouped = {}

    for a in alerts:
        key = _fixture_key(a["fixture"])
        grouped.setdefault(key, {"fixture": a["fixture"], "alerts": [], "prediction": None})
        grouped[key]["alerts"].append(a["result"])

    for p in predictions:
        fixture = {"league": p["league"], "date": p["date"], "home": p["home"], "away": p["away"]}
        key = _fixture_key(fixture)
        grouped.setdefault(key, {"fixture": fixture, "alerts": [], "prediction": None})
        grouped[key]["prediction"] = p["prediction"]

    reports = []
    for key, entry in grouped.items():
        fixture = entry["fixture"]
        home, away = fixture["home"], fixture["away"]
        parts = []

        if entry["prediction"]:
            parts.append(_describe_outcome(entry["prediction"], home, away))

        for alert_result in entry["alerts"]:
            parts.append(_describe_alert(alert_result, home, away))

        if not parts:
            continue

        # La "mejor apuesta" es la alerta con más margen sobre la línea, si hay
        # alguna; si no hay alertas pero sí predicción, se resalta el 1X2 más probable.
        best_bet = None
        if entry["alerts"]:
            best_alert = max(entry["alerts"], key=_confidence_score)
            market_label = MARKET_LABELS.get(best_alert["market"], best_alert["market"])
            best_bet = f"Over de {market_label} ({best_alert['projected_total']} vs. línea {best_alert['line_reference']})"
        elif entry["prediction"]:
            o = entry["prediction"]["outcome_probs"]
            favorite, pct = max(
                [(home, o["home_win"]), ("Empate", o["draw"]), (away, o["away_win"])],
                key=lambda t: t[1],
            )
            best_bet = f"{favorite} ({pct*100:.0f}%)"

        reports.append({
            "fixture": fixture,
            "narrative": " ".join(parts),
            "best_bet": best_bet,
        })

    return reports
