from datetime import datetime

STAT_LABELS = {"corners": "Corners", "cards": "Tarjetas"}


def _alert_card(alert: dict) -> str:
    fixture = alert["fixture"]
    result = alert["result"]
    market_label = STAT_LABELS.get(result["market"], result["market"])

    signals_html = ""
    for s in result["signals"]:
        signals_html += f"""
        <div class="signal">
          <span class="side">{s['side'].upper()}</span>
          ataca con promedio <b>{s['attack_avg']}</b> vs. rival que concede <b>{s['opponent_concede_avg']}</b> de promedio
        </div>"""

    return f"""
    <div class="alert-card">
      <div class="alert-header">
        <span class="league">{fixture['league']}</span>
        <span class="date">{fixture['date']}</span>
      </div>
      <div class="match">{fixture['home']} vs {fixture['away']}</div>
      <div class="market-tag">{market_label} — línea de referencia {result['line_reference']}</div>
      <div class="projected">Proyección combinada: <b>{result['projected_total']}</b></div>
      {signals_html}
      <div class="sample">Muestra: local {result['sample_sizes']['home']} partidos · visitante {result['sample_sizes']['away']} partidos</div>
    </div>
    """


def render(alerts: list, generated_at: str = None) -> str:
    generated_at = generated_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if alerts:
        cards_html = "\n".join(_alert_card(a) for a in alerts)
    else:
        cards_html = '<div class="empty">No se encontraron partidos con doble confirmación en esta corrida.</div>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bitácora de Valor — Alertas</title>
<style>
  :root {{
    --bg: #0f1115;
    --card-bg: #171a21;
    --border: #2a2e38;
    --text: #e8e9ec;
    --muted: #9198a8;
    --accent: #4ade80;
    --accent-soft: rgba(74, 222, 128, 0.12);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 0;
    padding: 24px 16px 60px;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 28px; }}
  .alert-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
  }}
  .alert-header {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
  .match {{ font-size: 16px; font-weight: 600; margin-bottom: 8px; }}
  .market-tag {{
    display: inline-block;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 12px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 999px;
    margin-bottom: 10px;
  }}
  .projected {{ font-size: 13px; margin-bottom: 8px; color: var(--muted); }}
  .projected b {{ color: var(--text); }}
  .signal {{ font-size: 13px; margin-bottom: 4px; color: var(--muted); }}
  .signal .side {{ color: var(--accent); font-weight: 700; font-size: 11px; margin-right: 4px; }}
  .signal b {{ color: var(--text); }}
  .sample {{ font-size: 11px; color: var(--muted); margin-top: 8px; opacity: 0.7; }}
  .empty {{ color: var(--muted); font-style: italic; padding: 24px 0; }}
  footer {{ text-align: center; color: var(--muted); font-size: 11px; margin-top: 40px; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>📋 Bitácora de Valor — Alertas</h1>
    <div class="subtitle">Corners y tarjetas · doble confirmación (ataque + defensa) · actualizado {generated_at}</div>
    {cards_html}
    <footer>Generado automáticamente vía GitHub Actions + API-Football</footer>
  </div>
</body>
</html>
"""
