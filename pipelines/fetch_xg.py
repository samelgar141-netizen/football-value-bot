import asyncio

import aiohttp
import pandas as pd
import understat

import config

_MAX_CONCURRENT = 5  # cap parallel requests to Understat to avoid rate limiting


async def _fetch_match_shots(u, match_id, semaphore):
    async with semaphore:
        try:
            return await u.get_match_shots(match_id)
        except Exception as e:
            print(f"  fetch_xg: shots unavailable for match {match_id} — {e}")
            return {'h': [], 'a': []}


async def _fetch_async():
    async with aiohttp.ClientSession() as session:
        u = understat.Understat(session)
        season_year = int('20' + config.SEASON[:2])
        matches = await u.get_league_results("EPL", season_year)

        # Fetch per-match shot data concurrently (get_league_results only returns xG)
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        shots_list = await asyncio.gather(
            *[_fetch_match_shots(u, m['id'], semaphore) for m in matches]
        )

    rows = []
    for m, shots_data in zip(matches, shots_list):
        try:
            shots_h = shots_data.get('h', [])
            shots_a = shots_data.get('a', [])

            # Shots on target = goals + saved shots (posts/blocks excluded per standard definition)
            sot_results = {'Goal', 'SavedShot'}

            rows.append({
                'date':                   m['datetime'],
                'home_team':              m['h']['title'],
                'away_team':              m['a']['title'],
                'xg_home':                float(m['xG']['h']),
                'xg_away':                float(m['xG']['a']),
                'shots_home':             len(shots_h),
                'shots_away':             len(shots_a),
                'shots_on_target_home':   sum(1 for s in shots_h if s.get('result') in sot_results),
                'shots_on_target_away':   sum(1 for s in shots_a if s.get('result') in sot_results),
            })
        except (KeyError, ValueError, TypeError) as e:
            print(f"  fetch_xg: skipping match {m.get('id', '?')} — {e}")
            continue

    return pd.DataFrame(rows)


def fetch_xg_data():
    df = asyncio.run(_fetch_async())

    if df.empty:
        raise RuntimeError(
            "fetch_xg_data: no matches returned from Understat. "
            "Season may not have started yet or the API may be unavailable."
        )

    df['date'] = pd.to_datetime(df['date'])

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.RAW_DIR / f'xg_data_{config.SEASON}.csv'
    df.to_csv(out_path, index=False)

    _validate_xg(df, out_path)
    return df


def _validate_xg(df, path):
    df_check = pd.read_csv(path, parse_dates=['date'])
    print(f"\n--- xg_data_{config.SEASON}.csv validation ---")
    print(f"Shape:   {df_check.shape[0]} rows × {df_check.shape[1]} columns")
    print(f"Columns: {list(df_check.columns)}")
    print(f"\nFirst 3 rows:")
    print(df_check.head(3).to_string(index=False))
    print(f"\nNull counts per column:")
    print(df_check.isnull().sum().to_string())
    null_xg = df_check[['xg_home', 'xg_away']].isnull().any(axis=1).sum()
    if null_xg:
        raise ValueError(
            f"xg_data_{config.SEASON}.csv: {null_xg} rows have null xG values."
        )
    zero_shots = (df_check['shots_home'] == 0).all() and (df_check['shots_away'] == 0).all()
    if zero_shots:
        print(f"  WARNING: all shot counts are 0 — per-match shot fetch may have failed.")
    else:
        avg_shots = df_check[['shots_home', 'shots_away']].mean().mean()
        print(f"  Avg shots per team per match: {avg_shots:.1f}")
    print(f"\nValidation passed.")
