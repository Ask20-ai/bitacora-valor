"""
Resuelve el ID numÃ©rico de cada liga en Highlightly (una sola vez) y guarda
tambiÃ©n la temporada mÃ¡s reciente disponible, en data/leagues.json.
"""
import json
import os

LEAGUES_FILE = "data/leagues.json"


def load_cached_leagues() -> dict:
    if os.path.exists(LEAGUES_FILE):
        with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cached_leagues(mapping: dict):
    os.makedirs(os.path.dirname(LEAGUES_FILE), exist_ok=True)
    with open(LEAGUES_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def _best_match(results: list, search_name: str, country: str = None):
    if not results:
        return None
    candidates = results
    if country:
        filtered = [r for r in results if r.get("country", {}).get("name", "").lower() == country.lower()]
        if filtered:
            candidates = filtered
    # Preferimos el que matchee mÃ¡s de cerca el nombre buscado
    search_lower = search_name.lower()
    exact = [r for r in candidates if r["name"].lower() == search_lower]
    if exact:
        return exact[0]
    contains = [r for r in candidates if search_lower in r["name"].lower() or r["name"].lower() in search_lower]
    if contains:
        return contains[0]
    return candidates[0]


def resolve_leagues(client, leagues_config: list) -> dict:
    """
    Devuelve {key: {"id": int, "name": str, "country": str, "latest_season": int}}
    Usa el cachÃ© en disco si ya existe; si falta alguna liga, la busca y la agrega.
    """
    from api_client import RateLimitExceeded  # import local para evitar dependencia circular

    cached = load_cached_leagues()
    changed = False

    for league in leagues_config:
        key = league["key"]
        if key in cached:
            continue
        try:
            results = client.search_leagues(league["search"], league.get("country"))
        except RateLimitExceeded:
            if changed:
                save_cached_leagues(cached)
            raise
        except Exception as e:
            # Errores transitorios (5xx del proveedor, timeouts, etc.) no
            # deben tirar abajo toda la corrida â€” se salta esta liga y se
            # reintenta sola en la prÃ³xima corrida (sigue sin estar en cached).
            print(f"[AVISO] Error buscando la liga '{key}', se salta esta corrida "
                  f"(se reintenta la prÃ³xima vez): {e}")
            continue
        best = _best_match(results, league["search"], league.get("country"))
        if not best:
            print(f"[DEBUG] BÃºsqueda '{league['search']}' (paÃ­s: {league.get('country')}) "
                  f"devolviÃ³ {len(results)} resultado(s) crudos de la API.")
            if results:
                nombres = [r.get("name") for r in results[:5]]
                print(f"[DEBUG] Primeros nombres devueltos: {nombres}")
            print(f"[AVISO] No se encontrÃ³ la liga '{league['search']}' "
                  f"(paÃ­s: {league.get('country')}). Revisala manualmente en Highlightly.")
            continue

        seasons = best.get("seasons", [])
        latest_season = max((s["season"] for s in seasons), default=None)

        cached[key] = {
            "id": best["id"],
            "name": best["name"],
            "country": best.get("country", {}).get("name"),
            "latest_season": latest_season,
        }
        changed = True
        print(f"[OK] Resuelta liga '{key}' -> id={cached[key]['id']} "
              f"({cached[key]['name']}), temporada mÃ¡s reciente: {latest_season}")

    if changed:
        save_cached_leagues(cached)

    return cached
