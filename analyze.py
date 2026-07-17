"""
Cálculo de promedios de corners/tarjetas por equipo y detección de "valor".

Regla central (tu metodología, post-mortem incluido):
- NUNCA se recomienda un over solo porque un equipo ataca mucho.
- Se exige ataque de un lado Y flojera defensiva comprobada del rival, para el
  MISMO mercado, con datos independientes (no la misma cifra repetida dos veces
  disfrazada de "confirmación").

Nota técnica: Highlightly no tiene un endpoint de "últimos N partidos"
configurable, así que usamos /last-five-games (fijo en 5) y para cada uno de
esos partidos pedimos /statistics/{matchId} para sacar corners/tarjetas.
"""
from statistics import mean
from config import THRESHOLDS

# Los nombres exactos de "displayName" pueden variar según la liga/proveedor,
# así que matcheamos por substring en vez de un nombre exacto.
STAT_NAME_MATCH = {
    "corners": ["corner"],
    "cards": ["yellow card"],
}


def _find_stat_value(team_stats_block: dict, keywords: list):
    for s in team_stats_block.get("statistics", []):
        name = (s.get("displayName") or "").lower()
        if any(kw in name for kw in keywords):
            value = s.get("value")
            if isinstance(value, str) and value.endswith("%"):
                return None
            return value
    return None


def team_rolling_stats(client, team_id: int, market: str):
    """
    Devuelve promedios A FAVOR y EN CONTRA del equipo para el mercado dado
    (corners o cards), sobre los últimos 5 partidos finalizados
    (limitación del endpoint last-five-games de Highlightly).
    """
    keywords = STAT_NAME_MATCH[market]
    try:
        recent_matches = client.last_five_games(team_id)
    except Exception as e:
        print(f"[AVISO] No se pudo traer last-five-games del equipo {team_id}: {e}")
        return {"for_avg": None, "against_avg": None, "sample_size": 0}

    for_values, against_values = [], []

    for match in recent_matches:
        match_id = match.get("id")
        if not match_id:
            continue
        try:
            stats = client.match_statistics(match_id)
        except Exception as e:
            print(f"[AVISO] No se pudo traer stats del partido {match_id}: {e}")
            continue

        if not stats:
            continue

        team_block = next((b for b in stats if b.get("team", {}).get("id") == team_id), None)
        opponent_block = next((b for b in stats if b.get("team", {}).get("id") != team_id), None)
        if not team_block:
            continue

        team_value = _find_stat_value(team_block, keywords)
        if team_value is not None:
            for_values.append(team_value)
        if opponent_block:
            opp_value = _find_stat_value(opponent_block, keywords)
            if opp_value is not None:
                against_values.append(opp_value)

    return {
        "for_avg": round(mean(for_values), 2) if for_values else None,
        "against_avg": round(mean(against_values), 2) if against_values else None,
        "sample_size": len(for_values),
    }


def evaluate_market(home_stats: dict, away_stats: dict, market: str):
    """
    Aplica la regla de doble confirmación para un mercado (corners o cards).
    Devuelve None si no hay valor, o un dict con el detalle si lo hay.
    """
    th = THRESHOLDS[market]
    signals = []

    if (home_stats["for_avg"] is not None and away_stats["against_avg"] is not None
            and home_stats["for_avg"] >= th["attack_min_avg"]
            and away_stats["against_avg"] >= th["defense_min_avg"]):
        signals.append({
            "side": "local",
            "attack_avg": home_stats["for_avg"],
            "opponent_concede_avg": away_stats["against_avg"],
        })

    if (away_stats["for_avg"] is not None and home_stats["against_avg"] is not None
            and away_stats["for_avg"] >= th["attack_min_avg"]
            and home_stats["against_avg"] >= th["defense_min_avg"]):
        signals.append({
            "side": "visitante",
            "attack_avg": away_stats["for_avg"],
            "opponent_concede_avg": home_stats["against_avg"],
        })

    if not signals:
        return None

    projected_total = (home_stats["for_avg"] or 0) + (away_stats["for_avg"] or 0)

    return {
        "market": market,
        "line_reference": th["line"],
        "projected_total": round(projected_total, 2),
        "signals": signals,
        "sample_sizes": {
            "home": home_stats["sample_size"],
            "away": away_stats["sample_size"],
        },
    }
