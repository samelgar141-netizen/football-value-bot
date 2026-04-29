import os
import requests
import pandas as pd
from dotenv import load_dotenv

import config

load_dotenv()


def _get_api_key():
    key = os.getenv('FOOTBALL_DATA_API_KEY')
    if not key:
        raise EnvironmentError(
            "Missing environment variable: FOOTBALL_DATA_API_KEY. "
            "Add it to your .env file."
        )
    return key


def fetch_results():
    key = _get_api_key()
    url = f'https://api.football-data.org/v4/competitions/{config.LEAGUE_ID}/matches'
    params = {'season': '20' + config.SEASON[:2], 'status': 'FINISHED'}
    headers = {'X-Auth-Token': key}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"fetch_results failed — HTTP {response.status_code}: {response.text}"
        )

    matches = response.json().get('matches', [])
    if not matches:
        raise RuntimeError("fetch_results: no FINISHED matches returned from API.")

    rows = []
    for m in matches:
        score = m.get('score', {}).get('fullTime', {})
        rows.append({
            'match_id':   m['id'],
            'date':       m['utcDate'],
            'home_team':  m['homeTeam']['name'],
            'away_team':  m['awayTeam']['name'],
            'home_goals': score.get('home'),
            'away_goals': score.get('away'),
            'status':     m['status'],
        })

    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df['home_goals'] = pd.to_numeric(df['home_goals'])
    df['away_goals'] = pd.to_numeric(df['away_goals'])

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.RAW_DIR / f'results_{config.SEASON}.csv'
    df.to_csv(out_path, index=False)

    _validate_results(df, out_path)
    return df


def _validate_results(df, path):
    df_check = pd.read_csv(path, parse_dates=['date'])
    print(f"\n--- results_{config.SEASON}.csv validation ---")
    print(f"Shape:   {df_check.shape[0]} rows × {df_check.shape[1]} columns")
    print(f"Columns: {list(df_check.columns)}")
    print(f"\nFirst 3 rows:")
    print(df_check.head(3).to_string(index=False))
    print(f"\nNull counts per column:")
    print(df_check.isnull().sum().to_string())
    null_goals = df_check[['home_goals', 'away_goals']].isnull().any(axis=1).sum()
    if null_goals:
        raise ValueError(
            f"results_2425.csv: {null_goals} FINISHED rows have null goals — "
            "check API response."
        )
    print(f"\nNo null goals in FINISHED matches. Validation passed.")


def fetch_standings():
    key = _get_api_key()
    url = f'https://api.football-data.org/v4/competitions/{config.LEAGUE_ID}/standings'
    params = {'season': '20' + config.SEASON[:2]}
    headers = {'X-Auth-Token': key}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"fetch_standings failed — HTTP {response.status_code}: {response.text}"
        )

    standings_data = response.json().get('standings', [])
    total_table = next(
        (s for s in standings_data if s.get('type') == 'TOTAL'),
        None
    )
    if total_table is None:
        raise RuntimeError("fetch_standings: TOTAL standings table not found in API response.")

    rows = []
    for entry in total_table['table']:
        rows.append({
            'position':        entry['position'],
            'team':            entry['team']['name'],
            'played':          entry['playedGames'],
            'won':             entry['won'],
            'drawn':           entry['draw'],
            'lost':            entry['lost'],
            'goals_for':       entry['goalsFor'],
            'goals_against':   entry['goalsAgainst'],
            'goal_difference': entry['goalDifference'],
            'points':          entry['points'],
        })

    df = pd.DataFrame(rows)

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.RAW_DIR / 'standings.csv'
    df.to_csv(out_path, index=False)

    _validate_standings(df, out_path)
    return df


def _validate_standings(df, path):
    df_check = pd.read_csv(path)
    print(f"\n--- standings.csv validation ---")
    print(f"Shape:   {df_check.shape[0]} rows × {df_check.shape[1]} columns")
    print(f"Columns: {list(df_check.columns)}")
    print(f"\nFirst 3 rows:")
    print(df_check.head(3).to_string(index=False))
    print(f"\nNull counts per column:")
    print(df_check.isnull().sum().to_string())
    if df_check.isnull().any().any():
        raise ValueError("standings.csv: unexpected null values found.")
    print(f"\nNo nulls found. Validation passed.")
