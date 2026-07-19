"""
Cliente delgado para la Highlightly Football API, vía RapidAPI
(https://rapidapi.com/highlightly-api-highlightly-api-default/api/football-highlights-api).
"""
import os
import json
import time
import requests
from datetime import datetime, timezone

BASE_URL = "https://football-highlights-api.p.rapidapi.com"
RAPIDAPI_HOST = "football-highlights-api.p.rapidapi.com"


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class RequestBudgetExceeded(Exception):
    pass


class RateLimitExceeded(Exception):
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

        if resp.status_code == 429:
            raise RateLimitExceeded(
                "RapidAPI devolvió 429 (Too Many Requests). Esto significa que ya se "
                "gastó la cuota diaria gratuita, o que falta confirmar la suscripción "
                "al plan Basic/Free en la pestaña 'Pricing' de la API en RapidAPI. "
                "Revisá tu panel de RapidAPI (My Apps -> Analytics) para confirmar cuánto "
                "consumo llevás hoy."
            )

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

    def matches_by_league_season(self, league_id: int, season: int, page_size: int = 100,
                                  max_pages: int = 6, permanent: bool = False):
        """
        Recorre TODAS las páginas de partidos de la temporada (no solo la
        primera), porque una liga con muchos partidos ya jugados (ej. MLS a
        mitad de temporada) puede tener más de 100 resultados — si nos
        quedamos con la primera página nada más, los partidos próximos
        pueden quedar "atrás" de partidos viejos y nunca aparecer.

        max_pages=6 cubre hasta 600 partidos (de sobra para una temporada
        completa de cualquiera de nuestras ligas). Cada página es un
        request, pero se cachea el resultado combinado entero, así que el
        costo solo se paga una vez por día (o para siempre, si permanent=True).

        permanent=False (default): usado para partidos próximos, que sí cambian
        día a día -> cache con vencimiento diario.
        permanent=True: usado para temporadas ya finalizadas (historial para el
        modelo de predicción), que nunca cambian -> cache para siempre.
        """
        if permanent:
            cache_key = f"matches_permanent_{league_id}_{season}"
        else:
            cache_key = f"matches_{league_id}_{season}_{_today_str()}"

        cache_path = self._cache_path(cache_key)
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        all_data = []
        for page in range(max_pages):
            offset = page * page_size
            params = {"leagueId": league_id, "season": season, "limit": page_size, "offset": offset}
            response = self._get("/matches", params)  # sin cache individual, cacheamos el combinado al final
            page_data = response.get("data", [])
            all_data.extend(page_data)
            if len(page_data) < page_size:
                break  # esta fue la última página

        combined = {"data": all_data}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(combined, f)
        return combined

    def last_five_games(self, team_id: int):
        # Mismo criterio: un equipo casi nunca juega más de una vez por día,
        # así que alcanza con pedir esto una vez por día por equipo.
        return self._get(
            "/last-five-games", {"teamId": team_id},
            cache_key=f"last5_{team_id}_{_today_str()}",
            cacheable=True,
        )

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
