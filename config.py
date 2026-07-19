"""
ConfiguraciÃ³n central de BitÃ¡cora de Valor.
AjustÃ¡ acÃ¡ las ligas, temporada y umbrales sin tocar el resto del cÃ³digo.
"""

# --- Ligas a seguir ---
# "search" es el texto que se usa para buscar la liga en el endpoint /leagues de API-Football.
# "country" ayuda a desambiguar (algunas ligas tienen nombres parecidos en distintos paÃ­ses).
#
# TEMPORAL: dejamos solo MLS activa para probar el flujo completo sin gastar
# toda la cuota diaria de golpe. Una vez que confirmemos que todo funciona
# bien de punta a punta, descomentamos el resto.
LEAGUES = [
    # {"key": "la_liga",         "search": "La Liga",         "country": "Spain"},
    # {"key": "bundesliga",      "search": "Bundesliga",      "country": "Germany"},
    # {"key": "premier_league",  "search": "Premier League",  "country": "England"},
    # {"key": "champions",       "search": "UEFA Champions League", "country": None},
    {"key": "mls",             "search": "Major League Soccer", "country": "USA"},
    # {"key": "liga_pro_ec",     "search": "Liga Pro",        "country": "Ecuador"},
    # {"key": "liga_mx",         "search": "Liga MX",         "country": "Mexico"},
    # {"key": "eliteserien",     "search": "Eliteserien",     "country": "Norway"},
]

# Nota: la temporada de cada liga se resuelve automÃ¡ticamente (se usa la mÃ¡s
# reciente que Highlightly tenga registrada para esa liga), asÃ­ que no hace
# falta configurarla a mano acÃ¡.

# CuÃ¡ntos dÃ­as hacia adelante mirar en busca de partidos prÃ³ximos
# NOTA: la MLS estuvo pausada por el Mundial (25 mayo - 16 julio 2026) y
# reciÃ©n retomÃ³. El calendario post-reanudaciÃ³n puede tener huecos, asÃ­ que
# ampliamos la ventana a 10 dÃ­as para no quedarnos sin partidos por una
# coincidencia de fechas. Se puede volver a 5 mÃ¡s adelante si hace falta.
LOOKAHEAD_DAYS = 10

# Los promedios de forma reciente usan los Ãºltimos 5 partidos de cada equipo
# (fijo, por una limitaciÃ³n del endpoint last-five-games de Highlightly).

# --- Umbrales para "hay valor" ---
# La regla es SIEMPRE doble confirmaciÃ³n: ataque de un equipo Y defensa floja del rival.
# No alcanza con que un solo equipo tenga buen promedio.
THRESHOLDS = {
    "corners": {
        "attack_min_avg": 5.5,   # promedio de corners A FAVOR del equipo atacante
        "defense_min_avg": 5.5,  # promedio de corners EN CONTRA del rival (que concede)
        "line": 9.5,             # lÃ­nea de referencia para over de corners del partido
    },
    "cards": {
        "attack_min_avg": 2.2,   # promedio de tarjetas A FAVOR (que recibe) el equipo
        "defense_min_avg": 2.2,  # promedio de tarjetas EN CONTRA que "provoca" el rival
        "line": 4.5,             # lÃ­nea de referencia para over de tarjetas del partido
    },
}

# Requests por corrida: lÃ­mite de seguridad para no pasarte del plan gratuito por accidente.
MAX_REQUESTS_PER_RUN = 90
