import uuid
from datetime import datetime

import pandas as pd

import config

_LEDGER_PATH = config.LEDGER_DIR / 'bets.csv'

_COLUMNS = [
    'bet_id', 'date_placed', 'home_team', 'away_team', 'market',
    'odds', 'stake_gbp', 'model_prob', 'ev',
    'result', 'profit_loss', 'running_bankroll', 'notes',
]


def initialise_ledger():
    config.LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    needs_header = (
        not _LEDGER_PATH.exists()
        or _LEDGER_PATH.stat().st_size == 0
    )
    if needs_header:
        pd.DataFrame(columns=_COLUMNS).to_csv(_LEDGER_PATH, index=False)
        print(f"Ledger initialised → {_LEDGER_PATH}")
    else:
        print(f"Ledger already exists → {_LEDGER_PATH}")


def log_bet(bet_dict):
    if not _LEDGER_PATH.exists():
        raise FileNotFoundError(
            f"log_bet: ledger not found at {_LEDGER_PATH}. "
            "Call initialise_ledger() first."
        )
    row = {col: None for col in _COLUMNS}
    row.update(bet_dict)
    row['bet_id'] = str(uuid.uuid4())
    row['date_placed'] = row.get('date_placed') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    df = pd.DataFrame([row], columns=_COLUMNS)
    df.to_csv(_LEDGER_PATH, mode='a', header=False, index=False)
    print(f"Bet logged: {row['bet_id']}  |  {row['home_team']} v {row['away_team']}  |  {row['market']}  |  £{row['stake_gbp']}")
    return row['bet_id']


def log_result(bet_id, result, actual_score=None):
    if not _LEDGER_PATH.exists():
        raise FileNotFoundError(f"log_result: ledger not found at {_LEDGER_PATH}.")

    df = pd.read_csv(_LEDGER_PATH, dtype={'result': str, 'notes': str})
    idx = df.index[df['bet_id'] == bet_id].tolist()
    if not idx:
        raise ValueError(f"log_result: bet_id '{bet_id}' not found in ledger.")

    i = idx[0]
    stake = float(df.at[i, 'stake_gbp'])
    odds  = float(df.at[i, 'odds'])

    result_lower = str(result).lower()
    if result_lower == 'win':
        profit_loss = round((odds - 1.0) * stake, 2)
    elif result_lower == 'loss':
        profit_loss = round(-stake, 2)
    elif result_lower == 'void':
        profit_loss = 0.0
    else:
        raise ValueError(f"log_result: result must be 'win', 'loss', or 'void', got '{result}'")

    # running_bankroll = last settled row's bankroll + this profit_loss
    settled = df[(df['result'].notna()) & (df['result'] != 'nan') & (df.index < i)]
    if settled.empty:
        prev_bankroll = config.BANKROLL
    else:
        prev_bankroll = float(settled.iloc[-1]['running_bankroll'])

    df.at[i, 'result']           = result_lower
    df.at[i, 'profit_loss']      = profit_loss
    df.at[i, 'running_bankroll'] = round(prev_bankroll + profit_loss, 2)
    if actual_score:
        df.at[i, 'notes'] = str(actual_score)

    df.to_csv(_LEDGER_PATH, index=False)
    print(f"Result logged: {bet_id}  |  {result_lower}  |  P/L £{profit_loss:+.2f}  |  Bankroll £{df.at[i, 'running_bankroll']:.2f}")


def get_summary():
    if not _LEDGER_PATH.exists():
        raise FileNotFoundError(f"get_summary: ledger not found at {_LEDGER_PATH}.")

    df = pd.read_csv(_LEDGER_PATH, dtype={'result': str, 'notes': str})
    total_bets   = len(df)
    settled      = df[df['result'].notna() & (df['result'] != 'nan')]
    settled_bets = len(settled)
    wins         = int((settled['result'] == 'win').sum())
    losses       = int((settled['result'] == 'loss').sum())
    total_staked = float(df['stake_gbp'].sum()) if total_bets else 0.0
    total_pl     = float(settled['profit_loss'].sum()) if settled_bets else 0.0
    roi_pct      = (total_pl / total_staked * 100) if total_staked else 0.0

    if settled_bets:
        current_bankroll = float(settled.iloc[-1]['running_bankroll'])
    else:
        current_bankroll = config.BANKROLL

    return {
        'total_bets':       total_bets,
        'settled_bets':     settled_bets,
        'wins':             wins,
        'losses':           losses,
        'total_staked':     round(total_staked, 2),
        'total_profit_loss': round(total_pl, 2),
        'roi_pct':          round(roi_pct, 2),
        'current_bankroll': round(current_bankroll, 2),
    }


def remove_bets(bet_ids):
    """Remove specific bet_ids from the ledger (use only for cleanup)."""
    if not _LEDGER_PATH.exists():
        return
    df = pd.read_csv(_LEDGER_PATH)
    df = df[~df['bet_id'].isin(bet_ids)]
    df.to_csv(_LEDGER_PATH, index=False)
