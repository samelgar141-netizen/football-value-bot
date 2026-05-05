# Football Value Betting Bot

A Python system that models Premier League match probabilities using a Poisson distribution, compares them against bookmaker odds, and surfaces value bets where the model's edge exceeds a configurable threshold. Results are auto-settled each week, tracked in an append-only ledger, and visualised in an HTML dashboard.

---

## What it does

1. Fetches the current season's results and standings from [football-data.org](https://www.football-data.org/)
2. **Auto-settles** any unsettled bets in the ledger by matching them against the latest results
3. Fetches upcoming fixture odds from [The Odds API](https://the-odds-api.com/)
4. Derives team attack/defence strength ratings from historical results (Poisson model)
5. Predicts match outcome probabilities (home win / draw / away win) via a Poisson score matrix
6. Calculates Expected Value (EV) for each market, removing the bookmaker margin first
7. Recommends fractional Kelly stakes for any bet where EV exceeds the configured threshold
8. Saves a ranked report to `reports/value_bets_latest.csv`
9. Generates an HTML dashboard (`reports/dashboard.html`) with P&L chart and summary
10. Auto-commits and pushes updated files to GitHub

---

## Current configuration

| Setting | Value | Location |
|---|---|---|
| League | Premier League | `config.py → LEAGUE_ID` |
| Season | 2025/26 | `config.py → SEASON` |
| Starting bankroll | £20 | `config.py → BANKROLL` |
| Minimum EV threshold | 20% | `config.py → MIN_EV_THRESHOLD` |
| Kelly fraction | 25% of full Kelly | `config.py → MAX_KELLY_FRACTION` |

---

## Setup (first time only)

### 1. Clone and install — Command Prompt

```
git clone https://github.com/samelgar141-netizen/football-value-bot.git
cd football-value-bot
pip install -r requirements.txt
```

### 2. Create your `.env` file — Command Prompt or text editor

Create a file called `.env` in the `football-value-bot` folder with your API keys:

```
FOOTBALL_DATA_API_KEY=your_football_data_key_here
ODDS_API_KEY=your_odds_api_key_here
```

- Free football-data.org key: https://www.football-data.org/client/register
- Free Odds API key: https://the-odds-api.com/#get-access

> `.env` is gitignored and will never be committed. You must create it manually on every machine you use.

---

## Weekly process

Follow these steps in order each week. Steps marked **[Command Prompt]** run on your local Windows machine. Steps marked **[Claude]** are done by asking Claude in this session.

---

### Step 1 — Pull the latest code — Command Prompt

Before running anything locally, make sure you have the latest code and ledger from GitHub:

```
cd football-value-bot
git pull origin main
```

Do this every week before Step 2, because Claude may have logged bets or made code changes since your last run.

---

### Step 2 — Run the weekly pipeline — Command Prompt

```
python run_weekly.py
```

This single command does everything automatically:

| Sub-step | What happens |
|---|---|
| Fetch results | Downloads all finished PL matches this season |
| **Auto-settle bets** | Matches finished results against unsettled ledger entries — logs win/loss/P&L automatically |
| Fetch fixtures | Downloads next 14 days of scheduled matches |
| Fetch odds | Downloads best available odds across configured bookmakers |
| Compute team stats | Recalculates attack/defence ratings from all results |
| Predict fixtures | Runs Poisson model for each upcoming fixture |
| Find value bets | Identifies fixtures where EV > 20%, ranks by edge |
| Generate report | Saves `reports/value_bets_latest.csv` |
| Generate dashboard | Saves `reports/dashboard.html` |
| Git push | Auto-commits and pushes all outputs to GitHub |

If any API call fails, the script falls back to the most recent cached CSV and continues.

---

### Step 3 — Review the value bets

Open `reports/value_bets_latest.csv` in Excel or `reports/dashboard.html` in your browser to see this week's recommended bets ranked by EV.

Filter to only the fixtures happening **this weekend** (Friday–Monday) — the report may include fixtures from the following weekend too.

---

### Step 4 — Place your bets with your bookmaker

Place whichever bets you decide to take. The Kelly stake column shows a suggested stake based on your current bankroll and the model's edge. Use your own judgement — you do not have to take every bet in the report.

---

### Step 5 — Log your bets — Claude

Tell Claude which bets you placed (all fixtures from the weekend just gone) and Claude will log them to `ledger/bets.csv`. Bets are grouped into **Betting Cohorts** (BC 1, BC 2, etc.) — each gameweek's bets automatically get the next cohort number.

After Claude logs the bets and pushes to GitHub, run this locally to sync:

```
git pull origin main
```

---

### Step 6 — Wait for results

No action needed after placing bets. The next time you run `python run_weekly.py` (Step 2 next week), the auto-settle step will look up the results and fill in the win/loss/P&L columns automatically.

---

### Step 7 — View your updated dashboard — browser

After Step 2 runs and pushes, open `reports/dashboard.html` in your browser. It shows:

- **Summary cards**: current bankroll, total P&L, ROI, bets settled, wins/losses, total staked
- **Bankroll chart**: toggle between **Date** view (one point per bet) and **Betting Cohort** view (one point per gameweek)
- **Settled bets table**: full history with score, result, P&L, and running bankroll per bet

---

## Keeping GitHub and local in sync

| Situation | Action |
|---|---|
| Claude logged or changed something | Run `git pull origin main` locally |
| You ran `run_weekly.py` locally | Git push happens automatically — GitHub updates itself |
| GitHub shows different data to your local files | Run `git pull origin main` locally |

---

## Betting Cohort system

Every bet in the ledger has a `betting_cohort` number (BC 1, BC 2, etc.) that groups bets placed in the same gameweek together.

- When Claude logs a new batch of bets, they automatically get the **next available cohort number**
- If unsettled bets already exist (from the same gameweek), new bets join that cohort
- Once all bets in a cohort are settled, the next batch starts a new cohort
- The dashboard Betting Cohort chart view shows one data point per cohort — the final bankroll after all bets in that gameweek are settled

---

## File reference

### Files committed to GitHub

| File | Updated by | Description |
|---|---|---|
| `ledger/bets.csv` | `run_weekly.py` / Claude | Append-only bet ledger — never overwritten |
| `reports/value_bets_latest.csv` | `run_weekly.py` | This week's value bets |
| `reports/dashboard.html` | `run_weekly.py` | HTML P&L dashboard |
| `data/processed/team_stats.csv` | `run_weekly.py` | Computed team ratings |

### Files NOT committed (gitignored)

| File | Description |
|---|---|
| `.env` | API keys — create manually on each machine |
| `data/raw/*` | Raw results/fixtures from football-data.org |
| `data/odds/*` | Raw odds snapshots from The Odds API |

---

## CSV schema reference

### `ledger/bets.csv`
| Column | Type | Description |
|---|---|---|
| bet_id | str | UUID for this bet |
| date_placed | date | When the bet was placed |
| home_team | str | Home team |
| away_team | str | Away team |
| market | str | home / draw / away |
| odds | float | Decimal odds taken |
| stake_gbp | float | Amount staked in £ |
| model_prob | float | Model probability at time of bet |
| ev | float | Expected value at time of bet |
| betting_cohort | int | Gameweek group number (BC 1, BC 2…) |
| result | str | win / loss / void (blank until auto-settled) |
| profit_loss | float | Net P&L for this bet |
| running_bankroll | float | Cumulative bankroll after settlement |
| notes | str | Actual score (filled by auto-settle) |

### `reports/value_bets_latest.csv`
| Column | Type | Description |
|---|---|---|
| date | datetime | UTC kick-off time |
| home_team | str | Home team |
| away_team | str | Away team |
| market | str | home / draw / away |
| model_prob | float | Model's estimated probability |
| bookmaker_odds | float | Best available decimal odds |
| ev | float | Expected value (e.g. 0.25 = +25%) |
| kelly_stake_gbp | float | Recommended stake in £ (fractional Kelly) |

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

---

## Manual bet logging (if needed)

Claude handles bet logging automatically. If you ever need to log manually:

```python
from ledger.ledger import log_bet

log_bet({
    'date_placed':  '2026-05-09',
    'home_team':    'Arsenal',
    'away_team':    'Chelsea',
    'market':       'home',       # 'home', 'draw', or 'away'
    'odds':         2.30,
    'stake_gbp':    1.50,
    'model_prob':   0.65,
    'ev':           0.495,
})
```

The `betting_cohort` is assigned automatically — no need to set it manually.

## Manual result logging (if needed)

Results are logged automatically by `run_weekly.py`. If you ever need to log manually:

```python
from ledger.ledger import log_result

log_result(
    bet_id='your-uuid-here',
    result='win',        # 'win', 'loss', or 'void'
    actual_score='2-1',  # optional
)
```

## P&L summary

```python
from ledger.ledger import get_summary

summary = get_summary()
for k, v in summary.items():
    print(f'{k}: {v}')
```

Returns: `total_bets`, `settled_bets`, `wins`, `losses`, `total_staked`, `total_profit_loss`, `roi_pct`, `current_bankroll`.

---

## Model limitations and responsible use

- **Data quality**: Team strength ratings are based on the current season only. Early in the season (fewer than ~8 games per team) ratings are unreliable.
- **No form weighting**: The model treats all historical matches equally. Recent form is not considered.
- **No xG**: Goals scored/conceded include fortunate goals and misses. Expected goals data would improve accuracy.
- **Kelly sizing**: Fractional Kelly (25% of full Kelly) is used to reduce variance. Even so, apply your own judgement before placing any bet.
- **This is not financial advice.** Sports betting carries risk of loss. Only bet what you can afford to lose.
