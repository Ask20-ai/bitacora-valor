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


def _prediction_card(pred_entry: dict) -> str:
    pred = pred_entry["prediction"]
    o = pred["outcome_probs"]

    scores_html = "".join(
        f'<div class="score-chip"><span class="score-val">{s["score"]}</span>'
        f'<span class="score-prob">{s["prob"]*100:.1f}%</span></div>'
        for s in pred["top_scores"][:3]
    )

    return f"""
    <div class="pred-card">
      <div class="alert-header">
        <span class="league">{pred_entry['league']}</span>
        <span class="date">{pred_entry['date']}</span>
      </div>
      <div class="match">{pred_entry['home']} vs {pred_entry['away']}</div>
      <div class="expected-goals">Goles esperados: <b>{pred['lambda_home']}</b> - <b>{pred['lambda_away']}</b></div>
      <div class="outcome-bar">
        <div class="outcome-seg home" style="flex-grow:{o['home_win']}">
          <span>Local {o['home_win']*100:.0f}%</span>
        </div>
        <div class="outcome-seg draw" style="flex-grow:{o['draw']}">
          <span>Empate {o['draw']*100:.0f}%</span>
        </div>
        <div class="outcome-seg away" style="flex-grow:{o['away_win']}">
          <span>Visitante {o['away_win']*100:.0f}%</span>
        </div>
      </div>
      <div class="scores-row">{scores_html}</div>
    </div>
    """


def render(alerts: list, predictions: list = None, generated_at: str = None, status_message: str = None) -> str:
    predictions = predictions or []
    generated_at = generated_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    status_html = ""
    if status_message:
        status_html = f'<div class="status-banner">⚠️ {status_message}</div>'

    if alerts:
        alerts_html = "\n".join(_alert_card(a) for a in alerts)
    else:
        alerts_html = '<div class="empty">No se encontraron partidos con doble confirmación en esta corrida.</div>'

    if predictions:
        predictions_html = "\n".join(_prediction_card(p) for p in predictions)
    else:
        predictions_html = '<div class="empty">Todavía no hay predicciones disponibles (el modelo puede estar entrenándose, o falta historial suficiente).</div>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bitácora de Valor</title>
<style>
  :root {{
    --bg: #0f1115;
    --card-bg: #171a21;
    --border: #2a2e38;
    --text: #e8e9ec;
    --muted: #9198a8;
    --accent: #4ade80;
    --accent-soft: rgba(74, 222, 128, 0.12);
    --blue: #60a5fa;
    --amber: #fbbf24;
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
  h2 {{ font-size: 17px; margin: 32px 0 12px; padding-top: 8px; border-top: 1px solid var(--border); }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 12px; }}
  .alert-card, .pred-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
  }}
  .alert-card {{ border-left: 3px solid var(--accent); }}
  .pred-card {{ border-left: 3px solid var(--blue); }}
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
  .expected-goals {{ font-size: 13px; color: var(--muted); margin-bottom: 12px; }}
  .expected-goals b {{ color: var(--text); }}
  .outcome-bar {{
    display: flex;
    height: 28px;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 14px;
    font-size: 11px;
    font-weight: 600;
  }}
  .outcome-seg {{ display: flex; align-items: center; justify-content: center; min-width: 40px; }}
  .outcome-seg.home {{ background: var(--accent); color: #06210f; }}
  .outcome-seg.draw {{ background: var(--muted); color: #06210f; }}
  .outcome-seg.away {{ background: var(--blue); color: #06210f; }}
  .scores-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .score-chip {{
    background: rgba(251, 191, 36, 0.12);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 8px;
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 56px;
  }}
  .score-val {{ font-size: 13px; font-weight: 700; color: var(--amber); }}
  .score-prob {{ font-size: 11px; color: var(--muted); }}
  .empty {{ color: var(--muted); font-style: italic; padding: 16px 0; }}
  .status-banner {{
    background: rgba(251, 191, 36, 0.12);
    border: 1px solid rgba(251, 191, 36, 0.4);
    color: var(--amber);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    margin-bottom: 20px;
  }}
  footer {{ text-align: center; color: var(--muted); font-size: 11px; margin-top: 40px; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>📋 Bitácora de Valor</h1>
    <div class="subtitle">Actualizado {generated_at}</div>
    {status_html}

    <h2>🎯 Alertas de valor (corners y tarjetas)</h2>
    <div class="subtitle">Doble confirmación: ataque de un equipo + defensa floja del rival</div>
    {alerts_html}

    <h2>📊 Predicciones (modelo Dixon-Coles)</h2>
    <div class="subtitle">Probabilidades 1X2 y marcadores más probables, basados en historial de goles</div>
    {predictions_html}

    <footer>Generado automáticamente vía GitHub Actions + Highlightly</footer>
  </div>
</body>
</html>
"""
