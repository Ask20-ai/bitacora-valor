"""
Cliente para API-Football (api-sports.io), vía RapidAPI.
https://rapidapi.com/api-sports/api/api-football

Distinto del cliente de Highlightly (api_client.py): esta API se usa
específicamente para el módulo de predicción (predictor/), porque tiene
datos históricos de varias temporadas y odds pre-partido.
"""
import os
import json
import time
import requests

BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"


class RequestBudgetExceeded(Exception):
    pass


class RateLimitExceeded(Exception):
    pass


class ApiFootballClient:
    def __init__(self, api_key: str, max_requests: int, cache_dir: str = "predictor/data/cache"):
        if not api_key:
            raise ValueError("Falta la API key (variable de entorno API_FOOTBALL_KEY)")
        self.api_key = api_key
        self.max_requests = max_requests
        self.requests_used = 0
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_path(self, cache_key: str) -> str:
        safe = cache_key.replace("/", "_").replace("?", "_").replace("&", "_")
        return os.path.join(self.cache_dir, f"{safe}.json")

    def _get(self, endpoint: str, params: dict = None, cache_key: str = None, cacheable: bool = False):
        if cacheable and cache_key:
            path = self._cache_path(cache_key)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

        if self.requests_used >= self.max_requests:
            raise RequestBudgetExceeded(
                f"Se alcanzó el límite de {self.max_requests} requests en esta corrida."
            )

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": RAPIDAPI_HOST,
        }
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params or {}, timeout=30)
        self.requests_used += 1

        if resp.status_code == 429:
            raise RateLimitExceeded(
                "API-Football (RapidAPI) devolvió 429. Revisá tu cuota diaria en el "
                "dashboard de RapidAPI, o si hace falta confirmar la suscripción al plan."
            )

        resp.raise_for_status()
        data = resp.json()

        # Aviso si el propio API-Football reporta error de cuota en el body
        if data.get("errors"):
            errors = data["errors"]
            if isinstance(errors, dict) and any("limit" in str(v).lower() for v in errors.values()):
                raise RateLimitExceeded(f"API-Football reportó error de cuota: {errors}")

        time.sleep(0.4)

        if cacheable and cache_key:
            path = self._cache_path(cache_key)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        return data

    def search_league(self, name: str, country: str = None):
        params = {"search": name}
        data = self._get("/leagues", params)
        results = data.get("response", [])
        if country:
            filtered = [r for r in results if r["country"]["name"].lower() == country.lower()]
            if filtered:
                results = filtered
        return results

    def finished_fixtures(self, league_id: int, season: int):
        """
        Trae TODOS los partidos finalizados de una liga/temporada. Se usa para
        armar el historial de resultados (goles) que alimenta el modelo.
        Cacheable de forma permanente por temporada completa, EXCEPTO la
        temporada en curso (que sigue sumando partidos nuevos) — ver results_store.py.
        """
        params = {"league": league_id, "season": season, "status": "FT"}
        data = self._get("/fixtures", params)
        return data.get("response", [])

    def upcoming_fixtures(self, league_id: int, season: int, next_n: int = 15):
        params = {"league": league_id, "season": season, "next": next_n}
        data = self._get("/fixtures", params)
        return data.get("response", [])
