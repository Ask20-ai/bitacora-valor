# Bitácora de Valor — Alertas automáticas

Sistema que revisa los próximos partidos de tus ligas, calcula promedios de
corners y tarjetas por equipo, y detecta partidos donde hay **doble
confirmación** (un equipo ataca mucho + el rival concede mucho) en el mismo
mercado. Corre solo, gratis, vía GitHub Actions (con tu repo en privado), y
publica los resultados en una página web gratuita en Netlify — sin que
Netlify tenga acceso a tu código.

Fuente de datos: **Highlightly Football API**.

## 1. Conseguir tu API key (gratis, sin tarjeta)

1. Registrate en RapidAPI y suscribite (gratis) a "Football Highlights API":
   https://rapidapi.com/highlightly-api-highlightly-api-default/api/football-highlights-api
2. En la página de esa API dentro de RapidAPI vas a ver tu **X-RapidAPI-Key**
   (es la misma para todas las APIs de RapidAPI a las que te suscribas).
3. El plan gratuito (Basic) da 100 requests/día, sin tarjeta de crédito.

## 2. Subir este proyecto a GitHub (repo PRIVADO)

1. Creá un repositorio nuevo en GitHub, por ejemplo `bitacora-valor`, marcado
   como **Private**.
2. Subí todos estos archivos y carpetas tal cual están.

## 3. Guardar tu API key de Highlightly como secreto

1. En tu repo: **Settings → Secrets and variables → Actions → New repository secret**
2. Nombre: `HIGHLIGHTLY_API_KEY`
3. Valor: tu key de Highlightly (o de RapidAPI, según por dónde te registraste)
4. Guardar.

## 4. Publicar la página con Netlify (repo se queda privado)

Con esto, Netlify nunca se conecta a tu repo de GitHub — el Action genera el
HTML y se lo sube directo a Netlify por su CLI. Netlify solo ve la página
final, no tu código.

1. Creá una cuenta gratis en https://app.netlify.com/signup
2. Una vez adentro, andá a **Sites → Add new site → Deploy manually**, y
   arrastrá cualquier carpeta vacía o un archivo `index.html` de prueba (esto
   es solo para que Netlify te cree un sitio y te dé un Site ID; el contenido
   real lo va a pisar el Action en cada corrida).
3. En ese sitio, andá a **Site configuration → General → Site details** y
   copiá el **Site ID**.
4. Andá a **User settings → Applications → Personal access tokens → New access token**
   y generá uno (dale cualquier nombre, ej. "bitacora-valor").
5. En tu repo de GitHub: **Settings → Secrets and variables → Actions**,
   agregá dos secretos más:
   - `NETLIFY_AUTH_TOKEN`: el personal access token que generaste
   - `NETLIFY_SITE_ID`: el Site ID que copiaste
6. Listo. Cada vez que corra el workflow, va a publicar `docs/index.html` en
   tu sitio de Netlify (la URL te la da Netlify, tipo
   `https://nombre-random.netlify.app`, y la podés personalizar desde
   **Site configuration → Domain management**).

## 5. Probarlo manualmente

1. Pestaña **Actions** en tu repo
2. Workflow "Actualizar Bitácora de Valor" → botón **Run workflow**
3. Mirá los logs: te dice qué ligas resolvió, cuántas alertas encontró,
   cuántos requests gastó, y si el deploy a Netlify salió bien.

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
- **Consumo de requests**: hay dos niveles de caché para gastar lo mínimo
  posible:
  - **Permanente**: estadísticas de partidos ya finalizados (`data/cache/match_stats_*.json`)
    nunca se vuelven a pedir, porque esos datos no cambian.
  - **Diario**: los partidos próximos de cada liga y los "últimos 5 partidos"
    de cada equipo (`data/cache/matches_*.json`, `data/cache/last5_*.json`)
    se piden una vez por día — si el workflow corre varias veces el mismo
    día (ej. a las 09:00 y a las 21:00), la segunda corrida reusa lo que ya
    se pidió a la mañana, sin gastar cuota de nuevo.
- **Este es un punto de partida**, no un sistema de apuestas "llave en mano".
  La calibración de los umbrales con tus propios resultados (como ya venís
  haciendo con tu tracker de ROI) es lo que le va a dar valor real con el
  tiempo.
