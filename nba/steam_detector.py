"""
Detecta "steam moves": cuando la probabilidad implícita de un lado se mueve
en la misma dirección, por encima de un umbral, en la MAYORÍA de las casas
de apuestas rastreadas, entre dos snapshots.

Esto NO es Reverse Line Movement en sentido estricto (para eso hace falta el
% de apuestas del público, que ningún proveedor accesible nos da) — es una
aproximación honesta: movimiento sincronizado entre casas suele indicar
dinero grande entrando de golpe, sin necesitar ese dato que no tenemos.
"""

STEAM_THRESHOLD = 0.04  # 4 puntos porcentuales de probabilidad implícita
MIN_BOOKS_AGREEING = 2  # al menos 2 casas deben moverse en la misma dirección


def detect_steam_move(history: list) -> dict:
    """
    history: lista de snapshots (ver line_store.record_snapshot), ordenada
    cronológicamente. Compara el snapshot más viejo contra el más nuevo.
    Devuelve None si no hay señal, o un dict con el detalle si la hay.
    """
    if len(history) < 2:
        return None

    oldest = history[0]
    newest = history[-1]

    oldest_by_book = {b["bookmaker"]: b for b in oldest["books"]}
    newest_by_book = {b["bookmaker"]: b for b in newest["books"]}

    home_moves, away_moves = [], []

    for bookmaker, new_book in newest_by_book.items():
        old_book = oldest_by_book.get(bookmaker)
        if not old_book:
            continue
        if old_book["home_prob"] is None or new_book["home_prob"] is None:
            continue

        delta_home = new_book["home_prob"] - old_book["home_prob"]
        if delta_home >= STEAM_THRESHOLD:
            home_moves.append((bookmaker, delta_home))
        elif -delta_home >= STEAM_THRESHOLD:
            away_moves.append((bookmaker, -delta_home))

    side, moves = None, None
    if len(home_moves) >= MIN_BOOKS_AGREEING and len(home_moves) >= len(away_moves):
        side, moves = "home", home_moves
    elif len(away_moves) >= MIN_BOOKS_AGREEING:
        side, moves = "away", away_moves

    if not side:
        return None

    avg_move = sum(m[1] for m in moves) / len(moves)

    return {
        "side": side,
        "home_team": newest["home_team"],
        "away_team": newest["away_team"],
        "commence_time": newest["commence_time"],
        "books_agreeing": len(moves),
        "avg_probability_shift": round(avg_move, 3),
        "from_timestamp": oldest["timestamp"],
        "to_timestamp": newest["timestamp"],
    }
