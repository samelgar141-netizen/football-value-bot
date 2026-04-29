import os
import requests
import pandas as pd
from dotenv import load_dotenv

import config

load_dotenv()

_SPORT_KEY = 'soccer_epl'
_ODDS_FORMAT = 'decimal'
_REGIONS = 'uk'


def _get_api_key():
    key = os.getenv('ODDS_API_KEY')
    if not key:
        raise EnvironmentError(
            "Missing environment variable: ODDS_API_KEY. "
            "Add it to your .env file."
        )
    return key


def fetch_odds():
    key = _get_api_key()
    url = f'https://api.the-odds-api.com/v4/sports/{_SPORT_KEY}/odds'
    params = {
        'apiKey':     key,
        'regions':    _REGIONS,
        'markets':    'h2h,totals',
        'oddsFormat': _ODDS_FORMAT,
        'bookmakers': ','.join(config.BOOKMAKERS),
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"fetch_odds failed — HTTP {response.status_code}: {response.text}"
        )

    events = response.json()
    if not events:
        print("fetch_odds: no events returned from The Odds API.")

    rows = []
    for event in events:
        home_team = event['home_team']
        away_team = event['away_team']

        best = {
            'home_odds':   None,
            'draw_odds':   None,
            'away_odds':   None,
            'over25_odds': None,
            'under25_odds': None,
            'bookmaker':   None,
        }

        for bm in event.get('bookmakers', []):
            if bm['key'] not in config.BOOKMAKERS:
                continue
            for market in bm.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        price = outcome['price']
                        name = outcome['name']
                        if name == home_team:
                            if best['home_odds'] is None or price > best['home_odds']:
                                best['home_odds'] = price
                                best['bookmaker'] = bm['title']
                        elif name == away_team:
                            if best['away_odds'] is None or price > best['away_odds']:
                                best['away_odds'] = price
                        elif name == 'Draw':
                            if best['draw_odds'] is None or price > best['draw_odds']:
                                best['draw_odds'] = price

                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        point = outcome.get('point', 0)
                        if abs(point - 2.5) > 0.01:
                            continue
                        price = outcome['price']
                        if outcome['name'] == 'Over':
                            if best['over25_odds'] is None or price > best['over25_odds']:
                                best['over25_odds'] = price
                        elif outcome['name'] == 'Under':
                            if best['under25_odds'] is None or price > best['under25_odds']:
                                best['under25_odds'] = price

        rows.append({
            'match_id':      event['id'],
            'home_team':     home_team,
            'away_team':     away_team,
            'commence_time': event['commence_time'],
            'home_odds':     best['home_odds'],
            'draw_odds':     best['draw_odds'],
            'away_odds':     best['away_odds'],
            'over25_odds':   best['over25_odds'],
            'under25_odds':  best['under25_odds'],
            'bookmaker':     best['bookmaker'],
        })

    df = pd.DataFrame(rows, columns=[
        'match_id', 'home_team', 'away_team', 'commence_time',
        'home_odds', 'draw_odds', 'away_odds',
        'over25_odds', 'under25_odds', 'bookmaker',
    ])
    df['commence_time'] = pd.to_datetime(df['commence_time'], utc=True)

    config.ODDS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.ODDS_DIR / 'odds_latest.csv'
    df.to_csv(out_path, index=False)

    _validate_odds(out_path)
    return df


def _validate_odds(path):
    df = pd.read_csv(path, parse_dates=['commence_time'])
    print(f"\n--- odds_latest.csv validation ---")
    print(f"Shape:   {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))
    print(f"\nNull counts per column:")
    print(df.isnull().sum().to_string())

    odds_cols = ['home_odds', 'draw_odds', 'away_odds']
    null_odds = df[odds_cols].isnull().any(axis=1).sum()
    if null_odds:
        raise ValueError(
            f"odds_latest.csv: {null_odds} rows have null h2h odds — "
            "check bookmaker coverage."
        )

    if not df.empty and not pd.api.types.is_datetime64_any_dtype(df['commence_time']):
        raise ValueError("odds_latest.csv: 'commence_time' did not parse as datetime.")

    unique_bookmakers = df['bookmaker'].nunique()
    print(f"\nUnique bookmakers captured: {unique_bookmakers}")
    print(f"Bookmakers: {sorted(df['bookmaker'].dropna().unique().tolist())}")
    print("Validation passed.")
