"""
Cliente para TheOddsAPI (https://theoddsapi.com), usado para rastrear el
movimiento de línea de NBA.

IMPORTANTE: esta API cambió de esquema más de una vez en los últimos años.
Antes de tu primera corrida real, confirmá contra su documentación actual
(https://theoddsapi.com/docs/) que:
  - la URL base sigue siendo https://api.theoddsapi.com
  - el header de autenticación sigue siendo x-api-key
  - el formato de precio que te devuelve (decimal vs. americano)
Si algo no coincide, avisame y ajustamos este archivo puntual.
"""
import os
import json
import time
import requests
from datetime import datetime, timezone

BASE_URL = "https://api.theoddsapi.com"


class RequestBudgetExceeded(Exception):
    pass


class OddsApiClient:
    def __init__(self, api_key: str, max_requests: int = 20):
        if not api_key:
            raise ValueError("Falta la API key (variable de entorno THE_ODDS_API_KEY)")
        self.api_key = api_key
        self.max_requests = max_requests
        self.requests_used = 0

    def _get(self, endpoint: str, params: dict = None):
        if self.requests_used >= self.max_requests:
            raise RequestBudgetExceeded(
                f"Se alcanzó el límite de {self.max_requests} requests en esta corrida."
            )
        headers = {"x-api-key": self.api_key}
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params or {}, timeout=30)
        self.requests_used += 1
        resp.raise_for_status()
        time.sleep(0.3)
        return resp.json()

    def get_moneyline_odds(self, sport_key: str = "basketball_nba"):
        """
        Devuelve la lista de partidos próximos con las cuotas de moneyline
        (h2h) de cada casa de apuestas disponible en el plan gratuito.
        """
        return self._get("/odds/", {"sport_key": sport_key, "markets": "h2h"})
