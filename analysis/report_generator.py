from datetime import date
from tabulate import tabulate

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
