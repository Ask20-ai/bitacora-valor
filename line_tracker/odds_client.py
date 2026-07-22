"""
Cliente para The Odds API (https://the-odds-api.com).

A diferencia de Highlightly (presupuesto diario), acá el límite es MENSUAL
(500 créditos/mes en el plan gratis), así que el control de gasto se guarda
en disco y persiste entre corridas — no alcanza con contarlo por corrida.
"""
import os
import json
import requests
from datetime import datetime, timezone

BASE_URL = "https://api.the-odds-api.com/v4"
USAGE_FILE = "line_tracker/data/usage.json"


class MonthlyBudgetExceeded(Exception):
    pass


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_usage() -> dict:
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("month") == _current_month():
            return data
    return {"month": _current_month(), "credits_used": 0}


def _save_usage(usage: dict):
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(usage, f, indent=2)


class OddsApiClient:
    def __init__(self, api_key: str, monthly_budget: int):
        if not api_key:
            raise ValueError("Falta la API key (variable de entorno ODDS_API_KEY)")
        self.api_key = api_key
        self.monthly_budget = monthly_budget
        self.usage = _load_usage()

    @property
    def credits_used_this_month(self) -> int:
        return self.usage["credits_used"]

    def get_odds(self, sport_key: str, markets: str, region: str):
        """
        Trae las cuotas actuales para un deporte. El costo real en créditos
        depende de cuántos mercados y regiones se piden (lo indica la propia
        respuesta en el header x-requests-last).
        """
        if self.usage["credits_used"] >= self.monthly_budget:
            raise MonthlyBudgetExceeded(
                f"Se alcanzó el presupuesto mensual de {self.monthly_budget} créditos. "
                "Esperá al reset del mes o subí el presupuesto si tu plan da más margen."
            )

        params = {
            "apiKey": self.api_key,
            "regions": region,
            "markets": markets,
            "oddsFormat": "american",
        }
        resp = requests.get(f"{BASE_URL}/sports/{sport_key}/odds", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # The Odds API informa el costo real de la request en este header
        cost = int(resp.headers.get("x-requests-last", "1"))
        self.usage["credits_used"] += cost
        _save_usage(self.usage)

        return data
