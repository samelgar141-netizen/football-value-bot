import os
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd
from dotenv import load_dotenv

import config

load_dotenv()

_LOOKAHEAD_DAYS = 14


def _get_api_key():
    key = os.getenv('FOOTBALL_DATA_API_KEY')
    if not key:
        raise EnvironmentError(
            "Missing environment variable: FOOTBALL_DATA_API_KEY. "
            "Add it to your .env file."
        )
    return key


def fetch_fixtures():
    key = _get_api_key()
    url = f'https://api.football-data.org/v4/competitions/{config.LEAGUE_ID}/matches'
    params = {'season': '20' + config.SEASON[:2], 'status': 'SCHEDULED'}
    headers = {'X-Auth-Token': key}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"fetch_fixtures failed — HTTP {response.status_code}: {response.text}"
        )

    matches = response.json().get('matches', [])

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=_LOOKAHEAD_DAYS)

    rows = []
    for m in matches:
        match_date = datetime.fromisoformat(m['utcDate'].replace('Z', '+00:00'))
        if match_date <= cutoff:
            rows.append({
                'match_id':  m['id'],
                'date':      m['utcDate'],
                'home_team': m['homeTeam']['name'],
                'away_team': m['awayTeam']['name'],
                'status':    m['status'],
            })

    if not rows:
        print("fetch_fixtures: no SCHEDULED fixtures found in the next 14 days.")

    df = pd.DataFrame(rows, columns=['match_id', 'date', 'home_team', 'away_team', 'status'])
    df['date'] = pd.to_datetime(df['date'], utc=True)

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.RAW_DIR / 'fixtures.csv'
    df.to_csv(out_path, index=False)

    _validate_fixtures(out_path)
    return df


def _validate_fixtures(path):
    df = pd.read_csv(path, parse_dates=['date'])
    print(f"\n--- fixtures.csv validation ---")
    print(f"Shape:   {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    print(f"\nAll rows:")
    if df.empty:
        print("  (no fixtures in next 14 days)")
    else:
        print(df.to_string(index=False))
    print(f"\nNull counts per column:")
    print(df.isnull().sum().to_string())
    if df.isnull().any().any():
        raise ValueError("fixtures.csv: unexpected null values found.")
    if not df.empty and not pd.api.types.is_datetime64_any_dtype(df['date']):
        raise ValueError("fixtures.csv: 'date' column did not parse as datetime.")
    print(f"\nDate column dtype: {df['date'].dtype}")
    print("Validation passed.")
