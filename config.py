"""
Configuración central de Bitácora de Valor.
Ajustá acá las ligas, temporada y umbrales sin tocar el resto del código.
"""

# --- Ligas a seguir ---
# "search" es el texto que se usa para buscar la liga en el endpoint /leagues de API-Football.
# "country" ayuda a desambiguar (algunas ligas tienen nombres parecidos en distintos países).
LEAGUES = [
    {"key": "la_liga",         "search": "La Liga",         "country": "Spain"},
    {"key": "bundesliga",      "search": "Bundesliga",      "country": "Germany"},
    {"key": "premier_league",  "search": "Premier League",  "country": "England"},
    {"key": "champions",       "search": "UEFA Champions League", "country": None},
    {"key": "mls",             "search": "MLS",             "country": "USA"},
    {"key": "liga_pro_ec",     "search": "Liga Pro",        "country": "Ecuador"},
    {"key": "liga_mx",         "search": "Liga MX",         "country": "Mexico"},
    {"key": "eliteserien",     "search": "Eliteserien",     "country": "Norway"},
]

# Nota: la temporada de cada liga se resuelve automáticamente (se usa la más
# reciente que Highlightly tenga registrada para esa liga), así que no hace
# falta configurarla a mano acá.

# Cuántos días hacia adelante mirar en busca de partidos próximos
LOOKAHEAD_DAYS = 5

# Los promedios de forma reciente usan los últimos 5 partidos de cada equipo
# (fijo, por una limitación del endpoint last-five-games de Highlightly).

# --- Umbrales para "hay valor" ---
# La regla es SIEMPRE doble confirmación: ataque de un equipo Y defensa floja del rival.
# No alcanza con que un solo equipo tenga buen promedio.
THRESHOLDS = {
    "corners": {
        "attack_min_avg": 5.5,   # promedio de corners A FAVOR del equipo atacante
        "defense_min_avg": 5.5,  # promedio de corners EN CONTRA del rival (que concede)
        "line": 9.5,             # línea de referencia para over de corners del partido
    },
    "cards": {
        "attack_min_avg": 2.2,   # promedio de tarjetas A FAVOR (que recibe) el equipo
        "defense_min_avg": 2.2,  # promedio de tarjetas EN CONTRA que "provoca" el rival
        "line": 4.5,             # línea de referencia para over de tarjetas del partido
    },
}

# Requests por corrida: límite de seguridad para no pasarte del plan gratuito por accidente.
MAX_REQUESTS_PER_RUN = 90
