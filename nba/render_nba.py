from datetime import datetime

SIDE_LABELS = {"home": "el LOCAL", "away": "el VISITANTE"}


def _steam_card(alert: dict) -> str:
    side_label = SIDE_LABELS.get(alert["side"], alert["side"])
    return f"""
    <div class="steam-card">
      <div class="alert-header">
        <span class="league">NBA</span>
        <span class="date">{alert['commence_time'][:16].replace('T',' ')}</span>
      </div>
      <div class="match">{alert['home_team']} vs {alert['away_team']}</div>
      <div class="steam-tag">📈 Steam move hacia {side_label}</div>
      <div class="steam-detail">
        {alert['books_agreeing']} casas de apuestas se movieron en la misma dirección
        (cambio promedio de probabilidad implícita: <b>{alert['avg_probability_shift']*100:.1f} pts</b>)
      </div>
      <div class="sample">Detectado entre {alert['from_timestamp'][:16].replace('T',' ')} y {alert['to_timestamp'][:16].replace('T',' ')} UTC</div>
    </div>
    """


def render_nba(steam_alerts: list, generated_at: str = None) -> str:
    generated_at = generated_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if steam_alerts:
        alerts_html = "\n".join(_steam_card(a) for a in steam_alerts)
    else:
        alerts_html = '<div class="empty">No se detectaron movimientos de línea sincronizados en esta corrida.</div>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bitácora NBA — Movimiento de línea</title>
<style>
  :root {{
    --bg: #0f1115; --card-bg: #171a21; --border: #2a2e38;
    --text: #e8e9ec; --muted: #9198a8; --accent: #fb923c; --accent-soft: rgba(251,146,60,0.12);
  }}
  * {{ box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 24px 16px 60px; }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 20px; }}
  .steam-card {{ background: var(--card-bg); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 10px; padding: 16px 18px; margin-bottom: 14px; }}
  .alert-header {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
  .match {{ font-size: 16px; font-weight: 600; margin-bottom: 8px; }}
  .steam-tag {{ display: inline-block; background: var(--accent-soft); color: var(--accent); font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; margin-bottom: 10px; }}
  .steam-detail {{ font-size: 13px; color: var(--muted); margin-bottom: 8px; }}
  .steam-detail b {{ color: var(--text); }}
  .sample {{ font-size: 11px; color: var(--muted); opacity: 0.7; }}
  .empty {{ color: var(--muted); font-style: italic; padding: 24px 0; }}
  .disclaimer {{ font-size: 12px; color: var(--muted); background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; }}
  footer {{ text-align: center; color: var(--muted); font-size: 11px; margin-top: 40px; }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>🏀 Bitácora NBA — Movimiento de línea</h1>
    <div class="subtitle">Actualizado {generated_at}</div>
    <div class="disclaimer">
      Esto detecta <b>steam moves</b> (movimiento sincronizado entre casas de apuestas),
      no Reverse Line Movement estricto — ese requeriría datos de % de apuestas del
      público que ningún proveedor accesible ofrece. Es una aproximación razonable,
      no una certeza.
    </div>
    {alerts_html}
    <p><a href="index.html">← Volver a la Bitácora de fútbol</a></p>
    <footer>Generado automáticamente vía GitHub Actions + TheOddsAPI</footer>
  </div>
</body>
</html>
"""
