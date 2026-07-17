"""
Cliente delgado para la Highlightly Football API, vía RapidAPI
(https://rapidapi.com/highlightly-api-highlightly-api-default/api/football-highlights-api).
"""
import os
import json
import time
import requests

BASE_URL = "https://football-highlights-api.p.rapidapi.com"
RAPIDAPI_HOST = "football-highlights-api.p.rapidapi.com"


class RequestBudgetExceeded(Exception):
    pass


class HighlightlyClient:
    def __init__(self, api_key: str, max_requests: int, cache_dir: str = "data/cache"):
        if not api_key:
            raise ValueError("Falta la API key (variable de entorno HIGHLIGHTLY_API_KEY)")
        self.api_key = api_key
        self.max_requests = max_requests
        self.requests_used = 0
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_path(self, cache_key: str) -> str:
        safe = cache_key.replace("/", "_").replace("?", "_").replace("&", "_")
        return os.path.join(self.cache_dir, f"{safe}.json")

    def _get(self, endpoint: str, params: dict = None, cache_key: str = None, cacheable: bool = False):
        """
        cacheable=True: si ya existe en disco, nunca vuelve a pedirlo a la API
        (usar solo para datos inmutables, como estadísticas de un partido ya finalizado).
        """
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
        resp.raise_for_status()
        data = resp.json()

        time.sleep(0.4)  # respeto básico del rate limit

        if cacheable and cache_key:
            path = self._cache_path(cache_key)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        return data

    def search_leagues(self, league_name: str = None, country_name: str = None):
        params = {}
        if league_name:
            params["leagueName"] = league_name
        if country_name:
            params["countryName"] = country_name
        data = self._get("/leagues", params)
        return data.get("data", [])

    def matches_by_league_season(self, league_id: int, season: int, limit: int = 100, offset: int = 0):
        params = {"leagueId": league_id, "season": season, "limit": limit, "offset": offset}
        return self._get("/matches", params)

    def last_five_games(self, team_id: int):
        return self._get("/last-five-games", {"teamId": team_id})

    def match_statistics(self, match_id: int):
        # Cacheable: un partido ya jugado no cambia sus estadísticas.
        try:
            return self._get(
                f"/statistics/{match_id}",
                cache_key=f"match_stats_{match_id}",
                cacheable=True,
            )
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []  # sin estadísticas disponibles para este partido
            raise
