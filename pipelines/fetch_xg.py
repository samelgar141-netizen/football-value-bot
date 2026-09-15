import asyncio

import aiohttp
import pandas as pd
import understat

import config


async def _fetch_async():
    async with aiohttp.ClientSession() as session:
        u = understat.Understat(session)
        season_year = int('20' + config.SEASON[:2])
        matches = await u.get_league_results("EPL", season_year)

    rows = []
    for m in matches:
        try:
            rows.append({
                'date':                   m['datetime'],
                'home_team':              m['h']['title'],
                'away_team':              m['a']['title'],
                'xg_home':                float(m['xG']['h']),
                'xg_away':                float(m['xG']['a']),
                'shots_home':             int(m['h'].get('shot', 0)),
                'shots_away':             int(m['a'].get('shot', 0)),
                'shots_on_target_home':   int(m['h'].get('shotsOnTarget', 0)),
                'shots_on_target_away':   int(m['a'].get('shotsOnTarget', 0)),
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
    print(f"\nNo null xG values. Validation passed.")
