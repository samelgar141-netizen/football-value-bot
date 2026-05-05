import json
from datetime import date
from tabulate import tabulate

import pandas as pd

import config

_REPORT_COLUMNS = [
    'date', 'home_team', 'away_team', 'market',
    'model_prob', 'bookmaker_odds', 'ev', 'kelly_stake_gbp',
]


def generate_report(value_bets_df):
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.REPORTS_DIR / 'value_bets_latest.csv'

    report_df = value_bets_df.reindex(columns=_REPORT_COLUMNS)
    report_df.to_csv(out_path, index=False)

    _validate_report(out_path)
    _print_console_report(report_df)

    return out_path


def _validate_report(path):
    import pandas as pd
    df = pd.read_csv(path)
    if list(df.columns) != _REPORT_COLUMNS:
        raise ValueError(
            f"report_generator: CSV columns mismatch.\n"
            f"  Expected: {_REPORT_COLUMNS}\n"
            f"  Got:      {list(df.columns)}"
        )
    print(f"report saved → {path}  ({len(df)} value bet(s))")


def _print_console_report(df):
    print()
    print("=" * 70)
    print(f"  VALUE BET REPORT — {date.today().strftime('%d %B %Y')}")
    print(f"  Bankroll: £{config.BANKROLL:,.0f}  |  EV threshold: {config.MIN_EV_THRESHOLD:.0%}")
    print("=" * 70)

    if df.empty:
        print("  No value bets found this week.")
    else:
        display = df.copy()
        display['fixture'] = display['home_team'] + ' v ' + display['away_team']
        display = display[['fixture', 'market', 'model_prob', 'bookmaker_odds',
                            'ev', 'kelly_stake_gbp']]
        display.columns = ['Fixture', 'Market', 'Model %', 'Odds', 'EV', 'Kelly £']
        display['Model %'] = (display['Model %'] * 100).round(1).astype(str) + '%'
        display['EV'] = (display['EV'] * 100).round(1).astype(str) + '%'
        print(tabulate(display, headers='keys', tablefmt='github', showindex=False))

    print("=" * 70)
    print()


def generate_html_report():
    """Generate an HTML dashboard from the settled bets in the ledger."""
    ledger_path = config.LEDGER_DIR / 'bets.csv'
    if not ledger_path.exists():
        return None

    df = pd.read_csv(ledger_path, dtype={'result': str, 'notes': str})
    settled = df[
        df['result'].notna() & (df['result'] != '') & (df['result'] != 'nan')
    ].copy().reset_index(drop=True)

    if settled.empty:
        wins = losses = 0
        total_staked = total_pl = roi = 0.0
        current_bankroll = float(config.BANKROLL)
    else:
        wins            = int((settled['result'] == 'win').sum())
        losses          = int((settled['result'] == 'loss').sum())
        total_staked    = round(float(settled['stake_gbp'].sum()), 2)
        total_pl        = round(float(settled['profit_loss'].sum()), 2)
        roi             = round(total_pl / total_staked * 100, 1) if total_staked else 0.0
        current_bankroll = round(float(settled.iloc[-1]['running_bankroll']), 2)

    # chart data — date view: one point per bet; cohort view: one point per cohort
    chart_date_labels  = ['Start']
    chart_date_values  = [float(config.BANKROLL)]
    for _, row in settled.iterrows():
        chart_date_labels.append(str(row['date_placed'])[:10])
        chart_date_values.append(round(float(row['running_bankroll']), 2))

    # cohort view: final bankroll after each cohort completes
    chart_cohort_labels = ['Start']
    chart_cohort_values = [float(config.BANKROLL)]
    if not settled.empty and 'betting_cohort' in settled.columns:
        for cohort_num, group in settled.groupby(
            pd.to_numeric(settled['betting_cohort'], errors='coerce'), sort=True
        ):
            last_bankroll = round(float(group.iloc[-1]['running_bankroll']), 2)
            chart_cohort_labels.append(f"BC {int(cohort_num)}")
            chart_cohort_values.append(last_bankroll)

    # table rows html
    table_rows = ''
    for _, row in settled.iterrows():
        result_class = 'win' if row['result'] == 'win' else 'loss'
        pl = float(row['profit_loss'])
        pl_str = f"+£{pl:.2f}" if pl >= 0 else f"-£{abs(pl):.2f}"
        ev_pct = f"{float(row['ev'])*100:.0f}%"
        cohort = int(row['betting_cohort']) if 'betting_cohort' in row and pd.notna(row['betting_cohort']) else '-'
        table_rows += f"""
        <tr>
            <td>BC {cohort}</td>
            <td>{row['date_placed']}</td>
            <td>{row['home_team']} v {row['away_team']}</td>
            <td>{row['market'].upper()}</td>
            <td>{row['odds']}</td>
            <td>£{float(row['stake_gbp']):.2f}</td>
            <td>{ev_pct}</td>
            <td class="{result_class}">{row['result'].upper()}</td>
            <td class="{result_class}">{pl_str}</td>
            <td>£{float(row['running_bankroll']):.2f}</td>
            <td>{row.get('notes','') or ''}</td>
        </tr>"""

    pl_colour = '#22c55e' if total_pl >= 0 else '#ef4444'
    pl_str    = f"+£{total_pl:.2f}" if total_pl >= 0 else f"-£{abs(total_pl):.2f}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Football Value Bot — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem; }}
  h1 {{ font-size: 1.6rem; font-weight: 700; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 2rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem; margin-bottom: 2rem; }}
  .card {{ background: #1e293b; border-radius: 10px; padding: 1.2rem; }}
  .card .label {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;
                  letter-spacing: 0.05em; margin-bottom: 0.4rem; }}
  .card .value {{ font-size: 1.5rem; font-weight: 700; }}
  .card .value.green {{ color: #22c55e; }}
  .card .value.red   {{ color: #ef4444; }}
  .card .value.blue  {{ color: #60a5fa; }}
  section {{ background: #1e293b; border-radius: 10px; padding: 1.5rem; margin-bottom: 2rem; }}
  section h2 {{ font-size: 1rem; font-weight: 600; margin-bottom: 1rem; color: #cbd5e1; }}
  .chart-wrap {{ position: relative; height: 280px; }}
  .toggle {{ display: inline-flex; background: #0f172a; border-radius: 8px; padding: 3px;
             margin-bottom: 1rem; }}
  .toggle button {{ background: none; border: none; color: #94a3b8; padding: 0.35rem 0.9rem;
                    border-radius: 6px; cursor: pointer; font-size: 0.82rem; transition: all .15s; }}
  .toggle button.active {{ background: #334155; color: #e2e8f0; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ text-align: left; padding: 0.6rem 0.8rem; color: #94a3b8;
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em;
        border-bottom: 1px solid #334155; }}
  td {{ padding: 0.65rem 0.8rem; border-bottom: 1px solid #1e293b; }}
  tr:hover td {{ background: #263148; }}
  .win  {{ color: #22c55e; font-weight: 600; }}
  .loss {{ color: #ef4444; font-weight: 600; }}
  .footer {{ text-align: center; color: #475569; font-size: 0.8rem; margin-top: 1rem; }}
</style>
</head>
<body>
<h1>Football Value Bot</h1>
<p class="subtitle">Generated {date.today().strftime('%d %B %Y')} &nbsp;|&nbsp; Starting bankroll: £{config.BANKROLL}</p>

<div class="cards">
  <div class="card">
    <div class="label">Current Bankroll</div>
    <div class="value blue">£{current_bankroll:.2f}</div>
  </div>
  <div class="card">
    <div class="label">Total P/L</div>
    <div class="value" style="color:{pl_colour}">{pl_str}</div>
  </div>
  <div class="card">
    <div class="label">ROI</div>
    <div class="value" style="color:{pl_colour}">{roi:+.1f}%</div>
  </div>
  <div class="card">
    <div class="label">Bets Settled</div>
    <div class="value">{wins + losses}</div>
  </div>
  <div class="card">
    <div class="label">Wins / Losses</div>
    <div class="value"><span class="win">{wins}W</span> / <span class="loss">{losses}L</span></div>
  </div>
  <div class="card">
    <div class="label">Total Staked</div>
    <div class="value">£{total_staked:.2f}</div>
  </div>
</div>

<section>
  <h2>Bankroll Over Time</h2>
  <div class="toggle">
    <button id="btnDate" class="active" onclick="setAxis('date')">Date</button>
    <button id="btnCohort" onclick="setAxis('cohort')">Betting Cohort</button>
  </div>
  <div class="chart-wrap">
    <canvas id="plChart"></canvas>
  </div>
</section>

<section>
  <h2>Settled Bets</h2>
  <table>
    <thead>
      <tr>
        <th>Cohort</th><th>Date</th><th>Fixture</th><th>Market</th><th>Odds</th>
        <th>Stake</th><th>EV</th><th>Result</th><th>P/L</th>
        <th>Bankroll</th><th>Score</th>
      </tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
</section>

<p class="footer">Football Value Bot &mdash; Poisson model, {config.MIN_EV_THRESHOLD:.0%} EV threshold</p>

<script>
const dateLabels   = {json.dumps(chart_date_labels)};
const dateData     = {json.dumps(chart_date_values)};
const cohortLabels = {json.dumps(chart_cohort_labels)};
const cohortData   = {json.dumps(chart_cohort_values)};

const ctx = document.getElementById('plChart').getContext('2d');
const chart = new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: dateLabels,
    datasets: [{{
      label: 'Bankroll (£)',
      data: dateData,
      borderColor: '#60a5fa',
      backgroundColor: 'rgba(96,165,250,0.1)',
      borderWidth: 2,
      pointBackgroundColor: '#60a5fa',
      pointRadius: 4,
      tension: 0.3,
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8', maxRotation: 30 }}, grid: {{ color: '#1e293b' }} }},
      y: {{
        ticks: {{ color: '#94a3b8', callback: v => '£' + v.toFixed(2) }},
        grid: {{ color: '#334155' }},
        beginAtZero: false,
      }}
    }}
  }}
}});

function setAxis(mode) {{
  chart.data.labels   = mode === 'date' ? dateLabels : cohortLabels;
  chart.data.datasets[0].data = mode === 'date' ? dateData : cohortData;
  chart.update();
  document.getElementById('btnDate').classList.toggle('active', mode === 'date');
  document.getElementById('btnCohort').classList.toggle('active', mode === 'cohort');
}}
</script>
</body>
</html>"""

    out_path = config.REPORTS_DIR / 'dashboard.html'
    out_path.write_text(html, encoding='utf-8')
    print(f"HTML dashboard saved → {out_path}")
    return out_path
