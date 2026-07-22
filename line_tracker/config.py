"""
Configuración del rastreador de movimiento de línea para NFL/NBA.
"""

# Claves de deporte según The Odds API (https://the-odds-api.com/sports-odds-data/sports-apis.html)
SPORTS = [
    {"key": "americanfootball_nfl", "label": "NFL"},
    {"key": "basketball_nba", "label": "NBA"},
]

# Mercados a rastrear: moneyline, spread (hándicap de puntos), total de puntos
MARKETS = "h2h,spreads,totals"
REGION = "us"

# Presupuesto MENSUAL de créditos (el plan gratis da 500/mes, no por día).
# Dejamos margen de seguridad.
MONTHLY_CREDIT_BUDGET = 450

# Umbral para considerar que un movimiento de línea es "significativo"
SPREAD_MOVE_THRESHOLD = 1.0     # puntos (ej. de -3.5 a -4.5)
MONEYLINE_MOVE_THRESHOLD = 15   # puntos americanos (ej. de -150 a -165)
TOTAL_MOVE_THRESHOLD = 1.0      # puntos de total (ej. de 47.5 a 48.5)
