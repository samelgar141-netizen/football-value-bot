import pandas as pd

import config


def implied_prob(decimal_odds):
    if decimal_odds <= 1.0:
        raise ValueError(f"implied_prob: decimal odds must be > 1.0, got {decimal_odds}")
    return 1.0 / decimal_odds


def remove_vig(home_odds, draw_odds, away_odds):
    raw_home = implied_prob(home_odds)
    raw_draw = implied_prob(draw_odds)
    raw_away = implied_prob(away_odds)
    total = raw_home + raw_draw + raw_away
    return raw_home / total, raw_draw / total, raw_away / total


def calculate_ev(model_prob, decimal_odds):
    return (model_prob * decimal_odds) - 1.0


def kelly_stake(model_prob, decimal_odds, bankroll, max_fraction):
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    full_kelly = (model_prob * decimal_odds - 1.0) / b
    if full_kelly <= 0:
        return 0.0
    return full_kelly * max_fraction * bankroll


def find_value_bets(predictions_df, odds_df):
    odds = odds_df.copy()

    # normalise commence_time → date for merging
    if 'commence_time' in odds.columns:
        odds['date'] = pd.to_datetime(odds['commence_time'], utc=True).dt.date

    merged = predictions_df.merge(
        odds,
        on=['home_team', 'away_team'],
        how='inner',
        suffixes=('', '_odds'),
    )

    if merged.empty:
        print("find_value_bets: no matching fixtures between predictions and odds.")
        return pd.DataFrame()

    rows = []
    for _, row in merged.iterrows():
        true_home, true_draw, true_away = remove_vig(
            row['home_odds'], row['draw_odds'], row['away_odds']
        )

        markets = [
            ('home',  row['home_win_prob'], row['home_odds'], true_home),
            ('draw',  row['draw_prob'],     row['draw_odds'], true_draw),
            ('away',  row['away_win_prob'], row['away_odds'], true_away),
        ]

        for market, model_prob, odds_val, no_vig_prob in markets:
            ev = calculate_ev(model_prob, odds_val)
            if ev <= config.MIN_EV_THRESHOLD:
                continue
            stake = kelly_stake(
                model_prob, odds_val,
                config.BANKROLL, config.MAX_KELLY_FRACTION,
            )
            rows.append({
                'date':             row.get('date', row.get('date_odds', '')),
                'home_team':        row['home_team'],
                'away_team':        row['away_team'],
                'market':           market,
                'model_prob':       round(model_prob, 4),
                'bookmaker_odds':   round(odds_val, 3),
                'no_vig_prob':      round(no_vig_prob, 4),
                'ev':               round(ev, 4),
                'kelly_stake_gbp':  round(stake, 2),
                'bookmaker':        row.get('bookmaker', ''),
            })

    if not rows:
        print(f"find_value_bets: pipeline ran correctly — 0 value bets found "
              f"(EV threshold: {config.MIN_EV_THRESHOLD:.0%}).")
        return pd.DataFrame(columns=[
            'date', 'home_team', 'away_team', 'market',
            'model_prob', 'bookmaker_odds', 'no_vig_prob',
            'ev', 'kelly_stake_gbp', 'bookmaker',
        ])

    result_df = pd.DataFrame(rows).sort_values('ev', ascending=False).reset_index(drop=True)
    return result_df
