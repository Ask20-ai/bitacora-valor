"""
Arma un informe en texto por partido, combinando:
- Las probabilidades del modelo Dixon-Coles (1X2 + marcador mÃ¡s probable)
- Las alertas de corners/tarjetas (doble confirmaciÃ³n ataque/defensa)

Es texto generado con reglas a partir de los nÃºmeros ya calculados â€” no es
una IA "adivinando" el partido. Todo lo que dice el informe es trazable a un
cÃ¡lculo concreto hecho antes en el pipeline.
"""

MARKET_LABELS = {"corners": "corners", "cards": "tarjetas"}
GOALS_MARKET_THRESHOLD = 0.60  # a partir de que probabilidad vale la pena mencionar BTTS/Over en el texto


def _fixture_key(fixture: dict) -> tuple:
    return (fixture["league"], fixture["date"], fixture["home"], fixture["away"])


def _describe_outcome(pred: dict, home: str, away: str) -> str:
    o = pred["outcome_probs"]
    home_pct, draw_pct, away_pct = o["home_win"] * 100, o["draw"] * 100, o["away_win"] * 100
    favorite, fav_pct = max([(home, home_pct), ("empate", draw_pct), (away, away_pct)], key=lambda t: t[1])

    if fav_pct >= 55:
        strength = f"{favorite} aparece como favorito claro ({fav_pct:.0f}%)"
    elif fav_pct >= 40:
        strength = f"{favorite} es el resultado mÃ¡s probable, pero sin ser un partido cerrado ({fav_pct:.0f}%)"
    else:
        strength = "es un partido muy parejo, sin un favorito definido"

    top = pred["top_scores"][0]
    text = (
        f"SegÃºn el modelo, {strength}. Se esperan {pred['lambda_home']} goles de {home} "
        f"y {pred['lambda_away']} de {away}; el marcador mÃ¡s probable es {top['score']} "
        f"({top['prob']*100:.0f}%)."
    )

    gm = pred.get("goals_markets")
    if gm:
        extra = []
        if gm["btts_yes"] >= GOALS_MARKET_THRESHOLD:
            extra.append(f"que ambos anoten ({gm['btts_yes']*100:.0f}%)")
        if gm["over_2.5"] >= GOALS_MARKET_THRESHOLD:
            extra.append(f"over 2.5 goles ({gm['over_2.5']*100:.0f}%)")
        if extra:
            text += " TambiÃ©n hay buena probabilidad de " + " y ".join(extra) + "."

    return text


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
        f"En {market_label}, hay doble confirmaciÃ³n del lado de {sides}: la proyecciÃ³n combinada "
        f"({total}) queda {strength} de la lÃ­nea de referencia ({line})."
    )


def _confidence_score(alert_result: dict) -> float:
    """QuÃ© tan por encima de la lÃ­nea estÃ¡ la proyecciÃ³n, en proporciÃ³n â€” para rankear cuÃ¡l alerta es mÃ¡s fuerte."""
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

        # La "mejor apuesta" es la alerta con mÃ¡s margen sobre la lÃ­nea, si hay
        # alguna; si no hay alertas pero sÃ­ predicciÃ³n, se resalta el 1X2 mÃ¡s probable.
        best_bet = None
        if entry["alerts"]:
            best_alert = max(entry["alerts"], key=_confidence_score)
            market_label = MARKET_LABELS.get(best_alert["market"], best_alert["market"])
            best_bet = f"Over de {market_label} ({best_alert['projected_total']} vs. lÃ­nea {best_alert['line_reference']})"
        elif entry["prediction"]:
            o = entry["prediction"]["outcome_probs"]
            gm = entry["prediction"].get("goals_markets", {})
            candidates = [
                (home, o["home_win"]),
                ("Empate", o["draw"]),
                (away, o["away_win"]),
            ]
            if gm:
                candidates.append(("Ambos anotan (BTTS)", gm["btts_yes"]))
                candidates.append(("Over 2.5 goles", gm["over_2.5"]))
            best_label, pct = max(candidates, key=lambda t: t[1])
            best_bet = f"{best_label} ({pct*100:.0f}%)"

        reports.append({
            "fixture": fixture,
            "narrative": " ".join(parts),
            "best_bet": best_bet,
        })

    return reports
