import numpy as np
import pandas as pd
from scipy.stats import poisson

import config

_MAX_GOALS = 10


def compute_team_stats(results_df):
    df = results_df.copy()
    df = df.dropna(subset=['home_goals', 'away_goals'])

    avg_home_scored = df['home_goals'].mean()
    avg_away_scored = df['away_goals'].mean()

    if avg_home_scored == 0 or avg_away_scored == 0:
        raise ValueError("compute_team_stats: league goal averages are zero — check results data.")

    teams = sorted(set(df['home_team'].unique()) | set(df['away_team'].unique()))
    rows = []

    for team in teams:
        home_games = df[df['home_team'] == team]
        away_games = df[df['away_team'] == team]

        if home_games.empty or away_games.empty:
            continue

        avg_h_scored   = home_games['home_goals'].mean()
        avg_h_conceded = home_games['away_goals'].mean()
        avg_a_scored   = away_games['away_goals'].mean()
        avg_a_conceded = away_games['home_goals'].mean()

        rows.append({
            'team':              team,
            'home_attack':       avg_h_scored   / avg_home_scored,
            'home_defence':      avg_h_conceded / avg_away_scored,
            'away_attack':       avg_a_scored   / avg_away_scored,
            'away_defence':      avg_a_conceded / avg_home_scored,
            'avg_home_scored':   avg_h_scored,
            'avg_home_conceded': avg_h_conceded,
            'avg_away_scored':   avg_a_scored,
            'avg_away_conceded': avg_a_conceded,
        })

    stats_df = pd.DataFrame(rows)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PROCESSED_DIR / 'team_stats.csv'
    stats_df.to_csv(out_path, index=False)

    _validate_team_stats(out_path)
    return stats_df


def _validate_team_stats(path):
    df = pd.read_csv(path)
    print(f"\n--- team_stats.csv validation ---")
    print(f"Shape:   {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst 5 rows:")
    print(df.head(5).to_string(index=False))
    print(f"\nNull counts per column:")
    print(df.isnull().sum().to_string())
    if df.isnull().any().any():
        raise ValueError("team_stats.csv: unexpected null values found.")
    print("Validation passed.")


def predict_match(home_team, away_team, team_stats_df):
    stats = team_stats_df.set_index('team')

    if home_team not in stats.index:
        raise ValueError(f"predict_match: '{home_team}' not found in team_stats.")
    if away_team not in stats.index:
        raise ValueError(f"predict_match: '{away_team}' not found in team_stats.")

    avg_home = team_stats_df['avg_home_scored'].mean()
    avg_away = team_stats_df['avg_away_scored'].mean()

    exp_home = (stats.loc[home_team, 'home_attack']
                * stats.loc[away_team, 'away_defence']
                * avg_home)
    exp_away = (stats.loc[away_team, 'away_attack']
                * stats.loc[home_team, 'home_defence']
                * avg_away)

    goals = np.arange(0, _MAX_GOALS + 1)
    home_probs = poisson.pmf(goals, exp_home)
    away_probs = poisson.pmf(goals, exp_away)

    score_matrix = np.outer(home_probs, away_probs)
    score_df = pd.DataFrame(
        score_matrix,
        index=[f'H{g}' for g in goals],
        columns=[f'A{g}' for g in goals],
    )

    home_win_prob = float(np.sum(np.tril(score_matrix, -1)))
    draw_prob     = float(np.sum(np.diag(score_matrix)))
    away_win_prob = float(np.sum(np.triu(score_matrix, 1)))

    return {
        'home_win_prob':      home_win_prob,
        'draw_prob':          draw_prob,
        'away_win_prob':      away_win_prob,
        'expected_home_goals': exp_home,
        'expected_away_goals': exp_away,
        'score_matrix':       score_df,
    }


def predict_all_fixtures(fixtures_df, team_stats_df):
    rows = []
    for _, fixture in fixtures_df.iterrows():
        home = fixture['home_team']
        away = fixture['away_team']
        try:
            pred = predict_match(home, away, team_stats_df)
        except ValueError as e:
            print(f"  Warning — skipping {home} vs {away}: {e}")
            continue
        rows.append({
            'date':               fixture['date'],
            'home_team':          home,
            'away_team':          away,
            'home_win_prob':      pred['home_win_prob'],
            'draw_prob':          pred['draw_prob'],
            'away_win_prob':      pred['away_win_prob'],
            'expected_home_goals': pred['expected_home_goals'],
            'expected_away_goals': pred['expected_away_goals'],
        })

    return pd.DataFrame(rows)
