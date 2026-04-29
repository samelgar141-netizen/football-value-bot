# Football Value Betting Bot

A Python system that models Premier League match probabilities using a Poisson distribution, compares them against bookmaker odds, and surfaces value bets where the model's edge exceeds a configurable threshold.

---

## What it does

1. Fetches the current season's results and standings from [football-data.org](https://www.football-data.org/)
2. Fetches upcoming fixture odds from [The Odds API](https://the-odds-api.com/)
3. Derives team attack/defence strength ratings from historical results
4. Predicts match outcome probabilities (home win / draw / away win) via a Poisson score matrix
5. Calculates Expected Value (EV) for each market, removing the bookmaker margin first
6. Recommends fractional Kelly stakes for any bet where EV exceeds the threshold
7. Saves a ranked report to `reports/value_bets_latest.csv`
8. Maintains an append-only bet ledger for tracking P&L over time

---

## Setup

```bash
git clone https://github.com/samelgar141-netizen/football-value-bot.git
cd football-value-bot
pip install -r requirements.txt
```

Create a `.env` file in the project root with your API keys:

```
FOOTBALL_DATA_API_KEY=your_football_data_key_here
ODDS_API_KEY=your_odds_api_key_here
```

- Get a free football-data.org key at: https://www.football-data.org/client/register
- Get a free Odds API key at: https://the-odds-api.com/#get-access

---

## How to run

```bash
python run_weekly.py
```

Run this once per week (ideally on a Monday or Tuesday before the weekend fixtures). The script will:

- Refresh all data from both APIs
- Recompute team strength ratings
- Generate `reports/value_bets_latest.csv`
- Print a formatted summary to the console

If an API call fails (e.g. rate limit or missing key), the script falls back to the most recent cached CSV and continues.

---

## How to log a bet

After reviewing `reports/value_bets_latest.csv`, record any bets you place:

```python
from ledger.ledger import initialise_ledger, log_bet

initialise_ledger()  # safe to call repeatedly — only creates file if absent

bet_id = log_bet({
    'home_team':  'Arsenal',
    'away_team':  'Chelsea',
    'market':     'home',       # 'home', 'draw', or 'away'
    'odds':       2.30,
    'stake_gbp':  50.00,
    'model_prob': 0.65,
    'ev':         0.50,
})
print(f"Logged bet: {bet_id}")
```

---

## How to log a result

Once the match has been played:

```python
from ledger.ledger import log_result

log_result(
    bet_id='your-uuid-here',
    result='win',           # 'win', 'loss', or 'void'
    actual_score='2-1',     # optional, stored in notes column
)
```

`profit_loss` and `running_bankroll` are calculated and written automatically.

---

## How to read your P&L summary

```python
from ledger.ledger import get_summary

summary = get_summary()
for k, v in summary.items():
    print(f'{k}: {v}')
```

Returns: `total_bets`, `settled_bets`, `wins`, `losses`, `total_staked`, `total_profit_loss`, `roi_pct`, `current_bankroll`.

---

## CSV schema reference

### `data/raw/results_2425.csv`
| Column | Type | Description |
|---|---|---|
| match_id | int | football-data.org match ID |
| date | datetime | UTC kick-off time |
| home_team | str | Home team name |
| away_team | str | Away team name |
| home_goals | int | Full-time home goals |
| away_goals | int | Full-time away goals |
| status | str | FINISHED |

### `data/raw/fixtures.csv`
| Column | Type | Description |
|---|---|---|
| match_id | int | football-data.org match ID |
| date | datetime | UTC kick-off time |
| home_team | str | Home team name |
| away_team | str | Away team name |
| status | str | SCHEDULED |

### `data/odds/odds_latest.csv`
| Column | Type | Description |
|---|---|---|
| match_id | str | Odds API event ID |
| home_team | str | Home team name |
| away_team | str | Away team name |
| commence_time | datetime | UTC kick-off time |
| home_odds | float | Best available decimal home win odds |
| draw_odds | float | Best available decimal draw odds |
| away_odds | float | Best available decimal away win odds |
| over25_odds | float | Best available over 2.5 goals odds |
| under25_odds | float | Best available under 2.5 goals odds |
| bookmaker | str | Bookmaker offering best home odds |

### `data/processed/team_stats.csv`
| Column | Type | Description |
|---|---|---|
| team | str | Team name |
| home_attack | float | Home attack strength (relative to league avg) |
| home_defence | float | Home defence weakness (relative to league avg) |
| away_attack | float | Away attack strength |
| away_defence | float | Away defence weakness |
| avg_home_scored | float | Average goals scored at home per game |
| avg_home_conceded | float | Average goals conceded at home per game |
| avg_away_scored | float | Average goals scored away per game |
| avg_away_conceded | float | Average goals conceded away per game |

### `reports/value_bets_latest.csv`
| Column | Type | Description |
|---|---|---|
| date | date | Fixture date |
| home_team | str | Home team name |
| away_team | str | Away team name |
| market | str | home / draw / away |
| model_prob | float | Model's estimated probability |
| bookmaker_odds | float | Best available decimal odds |
| ev | float | Expected value (e.g. 0.12 = +12%) |
| kelly_stake_gbp | float | Recommended stake in £ (fractional Kelly) |

### `ledger/bets.csv`
| Column | Type | Description |
|---|---|---|
| bet_id | str | UUID for this bet |
| date_placed | datetime | When the bet was logged |
| home_team | str | Home team |
| away_team | str | Away team |
| market | str | home / draw / away |
| odds | float | Decimal odds taken |
| stake_gbp | float | Amount staked in £ |
| model_prob | float | Model probability at time of bet |
| ev | float | Expected value at time of bet |
| result | str | win / loss / void (blank until settled) |
| profit_loss | float | Net P&L for this bet |
| running_bankroll | float | Cumulative bankroll after settlement |
| notes | str | Optional — e.g. actual score |

---

## Model limitations and responsible use

- **Data quality**: Team strength ratings are based on the current season only. Early in the season (fewer than ~8 games per team) ratings are unreliable.
- **No form weighting**: The model treats all historical matches equally. A team's recent form is not considered.
- **No xG**: Goals scored/conceded include fortunate goals and misses. Expected goals data would improve accuracy.
- **Name mismatches**: football-data.org and The Odds API use different team name formats. If no value bets are found despite plausible predictions, check for team name mismatches between the two sources.
- **Kelly sizing**: Fractional Kelly (25% of full Kelly) is used to reduce variance. Even so, the staking suggestions can be large when the model finds a big edge — apply your own judgement before placing any bet.
- **This is not financial advice.** Sports betting carries risk of loss. Only bet what you can afford to lose. Gambling should be entertainment, not income.
