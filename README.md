# Football Value Betting Bot

A Python system that models Premier League match probabilities using a Poisson distribution, compares them against bookmaker odds, and surfaces value bets where the model's edge exceeds a configurable threshold. Results are auto-settled each week, tracked in an append-only ledger, and visualised in an HTML dashboard.

---

## What it does

1. Fetches the current season's results and standings from [football-data.org](https://www.football-data.org/)
2. **Auto-settles** any unsettled bets in the ledger by matching them against the latest results
3. Fetches upcoming fixture odds from [The Odds API](https://the-odds-api.com/)
4. Derives team attack/defence strength ratings from historical results (Poisson model)
5. Predicts match outcome probabilities (home win / draw / away win / over 2.5 / under 2.5 / BTTS) via a Poisson score matrix
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

## Weekly commands — quick reference

Run these in order every week from inside your `football-value-bot` folder in PowerShell or Command Prompt.

### 1. Sync latest code from GitHub
```
git pull origin main
```

### 2. Run the full pipeline
```
python run_weekly.py
```
This fetches results, auto-settles bets, fetches fixtures and odds, runs the model, generates the report and dashboard, and pushes everything to GitHub automatically.

### 3. Review value bets
Open `reports/dashboard.html` in your browser. Go to the **Upcoming Bets** tab to see this week's recommended bets.

### 4. Log the bets you decide to place
In the Upcoming Bets tab, toggle each bet to **Yes**, then click **Log Selected Bets**. A command will be copied to your clipboard. Paste it into PowerShell and press Enter:
```
python -c "from ledger.ledger import log_bet; log_bet({...}); ..."
```

### 5. Push your logged bets to GitHub
```
git add ledger/bets.csv
git commit -m "Log BC X bets"
git push origin main
```

### 6. After results — next week
Repeat from step 1. The pipeline will auto-settle all bets from the previous week and update the dashboard.

---

## Weekly process — detailed

Follow these steps in order each week. Steps marked **[Command Prompt]** run on your local Windows machine.

---

### Step 1 — Pull the latest code — Command Prompt

Before running anything locally, make sure you have the latest code and ledger from GitHub:

```
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
| Find value bets | Identifies fixtures in the next 6 days where EV > 20%, ranks by edge |
| Generate report | Saves `reports/value_bets_latest.csv` |
| Generate dashboard | Saves `reports/dashboard.html` |
| Git push | Auto-commits and pushes all outputs to GitHub |

If any API call fails, the script falls back to the most recent cached CSV and continues.

---

### Step 3 — Review the value bets

Open `reports/dashboard.html` in your browser and go to the **Upcoming Bets** tab. Bets are ranked by EV (highest edge first) and filtered to fixtures in the next 6 days only.

> **Important:** The odds shown are a snapshot from when you ran the pipeline. Always verify the current price at the bookmaker before placing — odds move constantly.

---

### Step 4 — Place your bets with your bookmaker

Place whichever bets you decide to take. The Kelly £ column shows a suggested stake based on your current bankroll and the model's edge. Use your own judgement — you do not have to take every bet in the report.

---

### Step 5 — Log your bets — Command Prompt

In the **Upcoming Bets** tab, toggle each bet you placed to **Yes**, then click **Log Selected Bets**. A `python -c "..."` command is copied to your clipboard. Paste it into PowerShell inside the `football-value-bot` folder and press Enter.

Then push the updated ledger to GitHub:

```
git add ledger/bets.csv
git commit -m "Log BC X bets"
git push origin main
```

---

### Step 6 — Wait for results

No action needed after placing bets. The next time you run `python run_weekly.py` (Step 2 next week), the auto-settle step will look up the results and fill in the win/loss/P&L columns automatically.

---

### Step 7 — View your updated dashboard — browser

After Step 2 runs and pushes, open `reports/dashboard.html` in your browser. It shows:

- **Summary cards**: current bankroll, total P&L, ROI, bets settled, wins/losses, total staked
- **Bankroll chart**: toggle between **Date** view (one point per bet) and **Betting Cohort** view (one point per gameweek)
- **Settled bets table**: full history with fractional and decimal odds, score, result, P&L, and running bankroll per bet

---

## Keeping GitHub and local in sync

| Situation | Action |
|---|---|
| Claude logged or changed something | Run `git pull origin main` locally |
| You ran `run_weekly.py` locally | Git push happens automatically — GitHub updates itself |
| You logged bets manually | Run `git add ledger/bets.csv && git commit -m "..." && git push origin main` |
| GitHub shows different data to your local files | Run `git pull origin main` locally |

---

## Understanding the report columns

These columns appear in `reports/value_bets_latest.csv` and the Upcoming Bets tab of the dashboard.

---

### ODDS (UK) — e.g. 10/1

The bookmaker's price expressed as a UK fraction. This is converted from the decimal odds: `decimal - 1 = fraction`, so 11.0 decimal = 10/1.

This is the odds you look up at the bookmaker. Always verify the current price before placing — this is a snapshot from when the pipeline last ran.

---

### ODDS (DEC) — e.g. 11.0

The same price in decimal format (European standard). For every £1 staked you receive £11.0 back if you win (£10 profit + £1 stake returned).

The model captures the **best available price** across all configured bookmakers (Bet365, Betway, Sky Bet, Unibet, etc.) at the time of the run.

---

### MODEL % — e.g. 14.4%

The model's estimate of the true probability that this outcome occurs. Calculated as follows:

1. **Team ratings** — for each team, compute `home_attack`, `home_defence`, `away_attack`, `away_defence` as ratios relative to the league average (1.0 = average). A team with `home_attack = 1.3` scores 30% more than average at home.

2. **Recency weighting** — matches are weighted using exponential decay (`e^(-0.005 × days_ago)`). A match played 6 months ago counts for ~40% of a match played last week, so recent form matters more.

3. **Regression to mean** — ratings are shrunk toward 1.0 (league average) based on sample size, so early-season ratings with few games are not over-trusted.

4. **Expected goals** — `exp_home_goals = home_attack × away_defence × league_avg_home_goals`. This gives the expected number of goals each team will score.

5. **Poisson score matrix** — an 11×11 grid of every scoreline (0-0 to 10-10) is built. Each cell's probability uses the Poisson distribution parameterised by the expected goals.

6. **Dixon-Coles correction** — the four low-score cells (0-0, 1-0, 0-1, 1-1) are adjusted because raw Poisson systematically underestimates draws and overestimates low-scoring home wins.

7. **Market probability** — summing the right cells gives each market: draw = all diagonal cells (0-0, 1-1, 2-2…); over 2.5 = all cells where home + away goals > 2; BTTS = all cells where both scores ≥ 1.

---

### EV — e.g. 59%

Expected Value. The core signal — how much profit the model expects per £1 staked, expressed as a percentage.

**Formula:**
```
EV = (Model % × Decimal Odds) − 1
   = (0.144 × 11.0) − 1
   = 1.584 − 1
   = +58.4%
```

**What it means:** Over many bets at this price and probability, the model expects to make 58p profit per £1 staked. It does **not** mean you win on this individual bet — a single bet at 14.4% probability loses ~86% of the time. The edge only materialises over a large number of bets.

**Where the edge comes from:** The bookmaker's implied probability for 11.0 decimal odds is `1 ÷ 11.0 = 9.1%`. The model says the true probability is 14.4%. The difference — after stripping out the bookmaker's margin — is where the value sits.

Only bets with EV > 20% are shown (configurable in `config.py → MIN_EV_THRESHOLD`).

---

### KELLY £ — e.g. £0.29

The recommended stake in pounds, sized proportionally to the model's edge using the Kelly criterion.

**Formula:**
```
Full Kelly fraction = (Model % × Decimal Odds − 1) ÷ (Decimal Odds − 1)
                    = (0.144 × 11.0 − 1) ÷ (11.0 − 1)
                    = 0.584 ÷ 10.0
                    = 5.84% of bankroll

Stake = Full Kelly × 25% × Current Bankroll
      = 5.84% × 25% × £21.79
      = £0.32
```

The model uses **25% of full Kelly** (`MAX_KELLY_FRACTION = 0.25`) as a safety cap. Full Kelly maximises long-run growth but produces very large swings and is highly sensitive to model errors. At 25% of full Kelly the stakes are smaller but variance is much more manageable.

A larger EV and a higher model probability both produce a larger Kelly stake. A longer-shot bet (high odds, low model %) produces a smaller stake even if the EV is high.

---

## Betting Cohort system

Every bet in the ledger has a `betting_cohort` number (BC 1, BC 2, etc.) that groups bets placed in the same gameweek together.

- When you log a new batch of bets, they automatically get the **next available cohort number**
- If unsettled bets already exist (from the same gameweek), new bets join that cohort
- Once all bets in a cohort are settled, the next batch starts a new cohort
- The dashboard Betting Cohort chart view shows one data point per cohort — the final bankroll after all bets in that gameweek are settled

---

## File reference

### Files committed to GitHub

| File | Updated by | Description |
|---|---|---|
| `ledger/bets.csv` | `run_weekly.py` / manually | Append-only bet ledger — never overwritten |
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
| market | str | home / draw / away / over_2_5 / under_2_5 / btts_yes / btts_no |
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
| market | str | home / draw / away / over_2_5 / under_2_5 / btts_yes / btts_no |
| model_prob | float | Model's estimated probability (see MODEL % above) |
| bookmaker_odds | float | Best available decimal odds across configured bookmakers |
| fractional_odds | str | Same odds in UK fractional format (e.g. 10/1) |
| ev | float | Expected value — e.g. 0.25 = +25% (see EV above) |
| kelly_stake_gbp | float | Recommended stake in £ using fractional Kelly (see KELLY £ above) |
| bookmaker | str | Which bookmaker is offering the best odds |

### `data/processed/team_stats.csv`
| Column | Type | Description |
|---|---|---|
| team | str | Team name |
| home_attack | float | Home attack strength relative to league avg (1.0 = average) |
| home_defence | float | Home defence weakness relative to league avg |
| away_attack | float | Away attack strength |
| away_defence | float | Away defence weakness |
| avg_home_scored | float | Weighted average goals scored at home per game |
| avg_home_conceded | float | Weighted average goals conceded at home per game |
| avg_away_scored | float | Weighted average goals scored away per game |
| avg_away_conceded | float | Weighted average goals conceded away per game |

---

## Manual bet logging (if needed)

The dashboard handles bet logging automatically. If you ever need to log manually:

```python
from ledger.ledger import log_bet

log_bet({
    'date_placed':  '2026-05-09',
    'home_team':    'Arsenal',
    'away_team':    'Chelsea',
    'market':       'home',       # 'home', 'draw', 'away', 'over_2_5', 'under_2_5', 'btts_yes', 'btts_no'
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

## Planned improvements — next season

### xG (Expected Goals) integration
Currently the model uses actual goals scored/conceded to build team ratings. Swapping these for xG would remove noise from penalties, deflections, and goalkeeping outliers — giving a cleaner picture of a team's underlying quality.

**Source:** [Understat](https://understat.com) — free, covers the Premier League, accessible via the `understat` Python package (no API key needed).

**What changes:**
- `pipelines/fetch_stats.py` — add `fetch_xg()` using the `understat` package
- `models/poisson_model.py` — use xGH/xGA columns instead of actual goals in `compute_team_stats()`
- Everything downstream (value detector, report, dashboard) stays the same

**When:** Reset at the start of the 2026/27 season alongside the season data refresh.

---

## Model limitations and responsible use

- **Odds are a snapshot**: The report captures odds at the time `run_weekly.py` runs. Always verify the current price at the bookmaker before placing a bet.
- **Data quality**: Team strength ratings are based on the current season only. Early in the season (fewer than ~8 games per team) ratings are unreliable — the regression-to-mean prior helps but does not eliminate this.
- **No xG**: Goals scored/conceded include fortunate goals and misses. Expected goals data would improve accuracy.
- **Kelly sizing**: Fractional Kelly (25% of full Kelly) is used to reduce variance. Even so, apply your own judgement before placing any bet.
- **This is not financial advice.** Sports betting carries risk of loss. Only bet what you can afford to lose.
