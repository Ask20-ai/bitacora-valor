"""
Compara el snapshot de apertura contra el más reciente de cada partido, y
marca los casos donde el movimiento supera el umbral configurado.

Importante: esto detecta que la línea se movió "de forma llamativa", no
determina por sí solo si es sharp money (para eso hace falta cruzar con
% de apuestas vs. dinero, que se revisa a mano en Action Network).
"""


def _diff_or_none(a, b):
    if a is None or b is None:
        return None
    return round(b - a, 2)


def detect_movements(games_with_history: list, thresholds: dict) -> list:
    movements = []

    for game in games_with_history:
        history = game["history"]
        if len(history) < 2:
            continue  # todavía no hay con qué comparar

        opening = history[0]
        current = history[-1]

        spread_move = _diff_or_none(opening["spread_home"], current["spread_home"])
        total_move = _diff_or_none(opening["total"], current["total"])
        h2h_home_move = _diff_or_none(opening["h2h_home"], current["h2h_home"])

        flags = []
        if spread_move is not None and abs(spread_move) >= thresholds["spread"]:
            direction = "hacia el local" if spread_move < 0 else "hacia el visitante"
            flags.append(f"Spread se movió {abs(spread_move)} puntos {direction} "
                         f"({opening['spread_home']} → {current['spread_home']})")

        if total_move is not None and abs(total_move) >= thresholds["total"]:
            direction = "arriba" if total_move > 0 else "abajo"
            flags.append(f"Total se movió {direction} {abs(total_move)} puntos "
                         f"({opening['total']} → {current['total']})")

        if h2h_home_move is not None and abs(h2h_home_move) >= thresholds["moneyline"]:
            flags.append(f"Moneyline del local se movió {abs(h2h_home_move)} puntos "
                         f"({opening['h2h_home']} → {current['h2h_home']})")

        if flags:
            movements.append({
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "commence_time": game["commence_time"],
                "flags": flags,
                "opening": opening,
                "current": current,
            })

    return movements
