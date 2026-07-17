# Bitácora de Valor — Alertas automáticas

Sistema que revisa los próximos partidos de tus ligas, calcula promedios de
corners y tarjetas por equipo, y detecta partidos donde hay **doble
confirmación** (un equipo ataca mucho + el rival concede mucho) en el mismo
mercado. Corre solo, gratis, vía GitHub Actions, y publica los resultados en
una página web (GitHub Pages).

Fuente de datos: **Highlightly Football API**.

## 1. Conseguir tu API key (gratis, sin tarjeta)

1. Andá a https://highlightly.net/login y creá tu cuenta.
   - Alternativa si esa vía te da problemas de acceso: registrate en RapidAPI
     en https://rapidapi.com/highlightly-api-highlightly-api-default/api/football-highlights-api
     (las cuentas de Highlightly y RapidAPI son independientes entre sí, elegí una).
2. En tu dashboard vas a ver tu API key.
3. El plan gratuito (Basic) da 100 requests/día, sin tarjeta de crédito.

## 2. Subir este proyecto a GitHub

1. Creá un repositorio nuevo en GitHub, por ejemplo `bitacora-valor`.
2. Subí todos estos archivos y carpetas tal cual están.

## 3. Guardar tu API key como secreto

1. En tu repo: **Settings → Secrets and variables → Actions → New repository secret**
2. Nombre: `HIGHLIGHTLY_API_KEY`
3. Valor: tu key de Highlightly (o de RapidAPI, según por dónde te registraste)
4. Guardar.

> Si te registraste vía RapidAPI en vez de Highlightly directo, avisame:
> el endpoint cambia levemente (necesita un header adicional
> `x-rapidapi-host`) y hay que ajustar una línea en `api_client.py`.

## 4. Activar GitHub Pages

1. En tu repo: **Settings → Pages**
2. "Build and deployment" → Source: **Deploy from a branch**
3. Branch: `main`, carpeta: `/docs`
4. Guardar. Te va a dar una URL tipo
   `https://tu-usuario.github.io/bitacora-valor/`.

## 5. Probarlo manualmente

1. Pestaña **Actions** en tu repo
2. Workflow "Actualizar Bitácora de Valor" → botón **Run workflow**
3. Mirá los logs: te dice qué ligas resolvió, cuántas alertas encontró, y
   cuántos requests gastó.

## 6. Ajustar a tu gusto

Todo lo importante está en `config.py`:
- `LOOKAHEAD_DAYS`: cuántos días adelante mirar partidos
- `THRESHOLDS`: los umbrales de "ataque" y "defensa floja" para considerar
  que hay valor. Calibralos con el tiempo comparando contra resultados reales.

## Cosas a tener en cuenta

- **Promedios sobre 5 partidos fijos**: Highlightly no permite elegir cuántos
  partidos recientes mirar (usa siempre los últimos 5 vía el endpoint
  `last-five-games`). Es una limitación de la API, no del código.
- **Cobertura de ligas menores**: Liga Pro Ecuador y Eliteserien pueden tener
  estadísticas de partido (corners/tarjetas) menos completas que las ligas
  top-5 europeas. Si ves muchos partidos con `sample_size` bajo o en 0 para
  esas ligas, es la API, no un bug — el sistema simplemente no genera alerta
  ahí por falta de datos confiables (esto es intencional, para no inventar
  señales de la nada).
- **Consumo de requests**: el caché en `data/cache/` guarda estadísticas de
  partidos ya finalizados (esos datos no cambian), así que el consumo baja
  con el tiempo. Los partidos próximos y los "last five games" de cada
  equipo SÍ se piden de nuevo cada corrida.
- **Este es un punto de partida**, no un sistema de apuestas "llave en mano".
  La calibración de los umbrales con tus propios resultados (como ya venís
  haciendo con tu tracker de ROI) es lo que le va a dar valor real con el
  tiempo.
