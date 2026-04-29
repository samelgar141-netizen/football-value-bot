import time
from datetime import datetime, timezone

import pandas as pd

import config
from ledger.ledger import initialise_ledger


def _header():
    print()
    print("=" * 70)
    print(f"  FOOTBALL VALUE BOT — weekly run")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    print()


def _step(name, fn, *args, **kwargs):
    print(f"[{name}] starting…")
    try:
        result = fn(*args, **kwargs)
        print(f"[{name}] OK")
        return result
    except Exception as e:
        print(f"[{name}] FAILED — {e}")
        return None


def main():
    t0 = time.time()
    _header()

    initialise_ledger()
    print()

    # ── Step 2: fetch results & standings ─────────────────────────────────
    from pipelines.fetch_stats import fetch_results, fetch_standings
    results_df   = _step("fetch_results",   fetch_results)
    standings_df = _step("fetch_standings", fetch_standings)

    # fall back to cached CSV if live fetch failed
    if results_df is None and (config.RAW_DIR / f'results_{config.SEASON}.csv').exists():
        results_df = pd.read_csv(config.RAW_DIR / f'results_{config.SEASON}.csv')
        print(f"[fetch_results] using cached CSV ({len(results_df)} rows)")

    print()

    # ── Step 3: fetch fixtures ─────────────────────────────────────────────
    from pipelines.fetch_fixtures import fetch_fixtures
    fixtures_df = _step("fetch_fixtures", fetch_fixtures)

    if fixtures_df is None and (config.RAW_DIR / 'fixtures.csv').exists():
        fixtures_df = pd.read_csv(config.RAW_DIR / 'fixtures.csv')
        print(f"[fetch_fixtures] using cached CSV ({len(fixtures_df)} rows)")

    if fixtures_df is not None:
        print(f"  Fixtures found: {len(fixtures_df)}")
    print()

    # ── Step 4: fetch odds ────────────────────────────────────────────────
    from pipelines.fetch_odds import fetch_odds
    odds_df = _step("fetch_odds", fetch_odds)

    if odds_df is None and (config.ODDS_DIR / 'odds_latest.csv').exists():
        odds_df = pd.read_csv(config.ODDS_DIR / 'odds_latest.csv')
        print(f"[fetch_odds] using cached CSV ({len(odds_df)} rows)")

    if odds_df is not None:
        print(f"  Odds fixtures: {len(odds_df)}")
    print()

    # ── Step 5: compute team stats ────────────────────────────────────────
    from models.poisson_model import compute_team_stats
    stats_df = None
    if results_df is not None:
        stats_df = _step("compute_team_stats", compute_team_stats, results_df)
        if stats_df is not None:
            print(f"  Teams modelled: {len(stats_df)}")
    else:
        print("[compute_team_stats] SKIPPED — no results data available")
        cached = config.PROCESSED_DIR / 'team_stats.csv'
        if cached.exists():
            stats_df = pd.read_csv(cached)
            print(f"[compute_team_stats] using cached CSV ({len(stats_df)} teams)")
    print()

    # ── Step 6: predict fixtures ──────────────────────────────────────────
    from models.poisson_model import predict_all_fixtures
    predictions_df = None
    if stats_df is not None and fixtures_df is not None:
        predictions_df = _step("predict_all_fixtures", predict_all_fixtures,
                               fixtures_df, stats_df)
        if predictions_df is not None:
            print(f"  Fixtures predicted: {len(predictions_df)}")
    else:
        print("[predict_all_fixtures] SKIPPED — missing stats or fixtures data")
    print()

    # ── Step 7: find value bets ───────────────────────────────────────────
    from analysis.value_detector import find_value_bets
    value_bets_df = None
    if predictions_df is not None and odds_df is not None:
        value_bets_df = _step("find_value_bets", find_value_bets,
                              predictions_df, odds_df)
        if value_bets_df is not None:
            print(f"  Value bets found: {len(value_bets_df)}")
    else:
        print("[find_value_bets] SKIPPED — missing predictions or odds data")
    print()

    # ── Step 8: generate report ───────────────────────────────────────────
    from analysis.report_generator import generate_report
    report_path = None
    if value_bets_df is not None:
        report_path = _step("generate_report", generate_report, value_bets_df)
    else:
        print("[generate_report] SKIPPED — no value bets data")
    print()

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print("=" * 70)
    print(f"  Run complete in {elapsed:.1f}s")
    if value_bets_df is not None:
        print(f"  Value bets found: {len(value_bets_df)}")
    if report_path:
        print(f"  Report: {report_path}")
    print()
    print("  Next step: review reports/value_bets_latest.csv and log any")
    print("  bets you place using ledger/ledger.py")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
