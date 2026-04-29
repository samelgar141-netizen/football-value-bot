# Football Value Betting System — Claude Code Instructions

## Project overview

This is a Python-based football value betting system. It ingests match statistics
and bookmaker odds, models match probabilities using a Poisson distribution, detects
value bets by comparing model probabilities to implied odds, and tracks all bets and
results in a running ledger. All persistent data is stored in CSV files — there is
no SQL database.

---

## Core rules — read before every task

1. **Build one file at a time.** Complete each file fully before moving to the next.
2. **Validate every CSV before moving on.** After any script that writes a CSV, read
   it back and print a summary (shape, column names, first 3 rows, null count). Only
   proceed when the output looks correct.
3. **Never overwrite the bet ledger.** `ledger/bets.csv` is append-only. Never use
   `mode='w'` on this file after it has been created.
4. **Environment variables only for secrets.** API keys must be read from a `.env`
   file using `python-dotenv`. Never hardcode keys.
5. **Fail loudly.** If an API call fails or a CSV is missing, raise a clear error
   with the filename and reason — do not silently continue.
6. **One entry point.** `run_weekly.py` is the only script the user runs manually.
   All other scripts are imported as modules.
7. **No external databases.** Do not introduce SQLite, PostgreSQL, or any DB
   dependency. All storage is CSV.

---

## Repo structure

```
football-value-bot/
├── data/
│   ├── raw/
│   │   ├── results_2425.csv       # full season match results
│   │   ├── standings.csv          # current league table
│   │   └── fixtures.csv           # upcoming fixtures (refreshed weekly)
│   ├── odds/
│   │   └── odds_latest.csv        # bookmaker odds snapshot (refreshed weekly)
│   └── processed/
│       └── team_stats.csv         # computed attack/defence strength ratings
├── models/
│   └── poisson_model.py           # Poisson probability model
├── pipelines/
│   ├── fetch_stats.py             # pulls results + standings from football-data.org
│   ├── fetch_odds.py              # pulls odds from The Odds API
│   └── fetch_fixtures.py          # pulls upcoming fixtures
├── analysis/
│   ├── value_detector.py          # EV calculation + Kelly stake sizing
│   └── report_generator.py        # produces ranked weekly value bet report
├── ledger/
│   └── bets.csv                   # running bet log — append-only
├── reports/
│   └── value_bets_latest.csv      # this week's output
├── config.py                      # league IDs, bankroll, thresholds (no secrets)
├── .env                           # API keys — never commit this
├── .gitignore                     # must include .env and data/raw/*
├── requirements.txt               # all dependencies
├── CLAUDE.md                      # this file
└── run_weekly.py                  # single entry point
```

---

## Build order — follow this sequence exactly

Work through each stage in order. Do not start the next stage until the current
stage's CSV validation has passed.

---

### Stage 1 — Project scaffold

**Task:** Create the full folder structure above with empty placeholder files.
Create `requirements.txt` with initial dependencies:
`requests`, `pandas`, `numpy`, `scipy`, `python-dotenv`, `tabulate`

Create `.gitignore` including: `.env`, `__pycache__/`, `*.pyc`, `data/raw/*`,
`data/odds/*` (raw fetched data should not be committed — processed and ledger files
should be).

**Validation:** Print the folder tree. Confirm all directories and placeholder files
exist.

---

### Stage 2 — config.py

**Task:** Create `config.py` with the following (no secrets):

- `LEAGUE_ID` = `'PL'` (Premier League — adjustable)
- `SEASON` = `'2425'`
- `BANKROLL` = `1000` (starting bankroll in £, adjustable)
- `MIN_EV_THRESHOLD` = `0.05` (only flag bets with EV > 5%)
- `MAX_KELLY_FRACTION` = `0.25` (cap Kelly stake at 25% of full Kelly for safety)
- `BOOKMAKERS` = list of bookmaker keys to pull from The Odds API
- `DATA_DIR`, `RAW_DIR`, `ODDS_DIR`, `PROCESSED_DIR`, `LEDGER_DIR`, `REPORTS_DIR`
  as `pathlib.Path` objects

**Validation:** Import config in a test snippet and print all values. Confirm paths
resolve correctly.

---

### Stage 3 — fetch_stats.py

**Task:** Build `pipelines/fetch_stats.py` as a module with two functions:

`fetch_results()` — calls football-data.org `/competitions/{LEAGUE_ID}/matches`
for the current season, filters to FINISHED matches, and saves to
`data/raw/results_2425.csv` with columns:
`match_id, date, home_team, away_team, home_goals, away_goals, status`

`fetch_standings()` — calls `/competitions/{LEAGUE_ID}/standings`, extracts the
total standings table, saves to `data/raw/standings.csv` with columns:
`position, team, played, won, drawn, lost, goals_for, goals_against, goal_difference, points`

API key read from `.env` as `FOOTBALL_DATA_API_KEY`.

**Validation:** After saving each CSV, read it back with pandas and print:

- Shape (rows × columns)
- Column names
- First 3 rows
- Count of any null values per column
- Confirm no rows have null `home_goals` or `away_goals` (for finished matches)

Only proceed when both CSVs pass validation.

---

### Stage 4 — fetch_fixtures.py

**Task:** Build `pipelines/fetch_fixtures.py` as a module with one function:

`fetch_fixtures()` — calls football-data.org `/competitions/{LEAGUE_ID}/matches`
filtered to SCHEDULED status, saves the next 14 days of fixtures to
`data/raw/fixtures.csv` with columns:
`match_id, date, home_team, away_team, status`

**Validation:** Print shape, columns, all rows (fixtures are few), confirm date
column parses correctly as datetime, confirm no nulls.

---

### Stage 5 — fetch_odds.py

**Task:** Build `pipelines/fetch_odds.py` as a module with one function:

`fetch_odds()` — calls The Odds API `/sports/soccer_epl/odds` with markets
`h2h` (match result) and `totals` (over/under 2.5). For each fixture, capture
the best available odds across all bookmakers in `config.BOOKMAKERS`. Save to
`data/odds/odds_latest.csv` with columns:
`match_id, home_team, away_team, commence_time, home_odds, draw_odds, away_odds, over25_odds, under25_odds, bookmaker`

API key read from `.env` as `ODDS_API_KEY`.

**Validation:** Print shape, columns, first 3 rows, confirm no null odds values,
confirm `commence_time` parses as datetime, print count of unique bookmakers captured.

---

### Stage 6 — poisson_model.py

**Task:** Build `models/poisson_model.py` as a module. This is the core model.

`compute_team_stats(results_df)` — from the season results CSV, compute for each
team: `attack_strength`, `defence_strength` (using the Dixon-Coles style average
goals method). Save output to `data/processed/team_stats.csv` with columns:
`team, home_attack, home_defence, away_attack, away_defence, avg_home_scored, avg_home_conceded, avg_away_scored, avg_away_conceded`

`predict_match(home_team, away_team, team_stats_df)` — returns a dict with:
`home_win_prob`, `draw_prob`, `away_win_prob`, `expected_home_goals`,
`expected_away_goals`, and a `score_matrix` (DataFrame of score probabilities up to 6-6)

`predict_all_fixtures(fixtures_df, team_stats_df)` — runs `predict_match` for
every upcoming fixture, returns a DataFrame with the above probability columns
alongside `home_team`, `away_team`, `date`.

**Validation:**

- Print `team_stats.csv` shape and first 5 rows
- Run `predict_match` for one hardcoded fixture (e.g. Arsenal vs Chelsea) and
  print the full probability dict including score matrix
- Confirm all three match outcome probabilities sum to 1.0 (within 0.001)

---

### Stage 7 — value_detector.py

**Task:** Build `analysis/value_detector.py` as a module with these functions:

`implied_prob(decimal_odds)` — converts decimal odds to implied probability

`remove_vig(home_odds, draw_odds, away_odds)` — normalises implied probs to
remove the bookmaker margin, returns `(true_home_prob, true_draw_prob, true_away_prob)`

`calculate_ev(model_prob, decimal_odds)` — returns `EV = (model_prob × decimal_odds) − 1`

`kelly_stake(model_prob, decimal_odds, bankroll, max_fraction)` — returns
recommended £ stake using fractional Kelly, capped at `max_fraction`

`find_value_bets(predictions_df, odds_df)` — merges model predictions with odds,
runs EV calculation for home/draw/away on every fixture, filters to rows where
EV > `MIN_EV_THRESHOLD`, adds Kelly stake column, sorts by EV descending.
Returns a DataFrame.

**Validation:** Run `find_value_bets` with the current predictions and odds CSVs.
Print the full output. For each value bet found, print:
`fixture | market | model prob | implied prob (no vig) | EV | Kelly stake (£)`

If no value bets are found, print a message confirming the function ran correctly
with zero results — do not treat this as an error.

---

### Stage 8 — report_generator.py

**Task:** Build `analysis/report_generator.py` as a module with one function:

`generate_report(value_bets_df)` — saves the value bets DataFrame to
`reports/value_bets_latest.csv`. Also prints a formatted console summary table
using `tabulate` showing all value bets ranked by EV. Include a header with
today's date and the bankroll used.

**Validation:** Confirm the CSV saves correctly. Print the console report.
Check that the CSV columns match exactly:
`date, home_team, away_team, market, model_prob, bookmaker_odds, ev, kelly_stake_gbp`

---

### Stage 9 — ledger/bets.csv + logging functions

**Task:** Define the ledger schema and create helper functions in a new file
`ledger/ledger.py`:

`initialise_ledger()` — creates `ledger/bets.csv` with headers if it does not
already exist. Columns:
`bet_id, date_placed, home_team, away_team, market, odds, stake_gbp, model_prob, ev, result, profit_loss, running_bankroll, notes`

`log_bet(bet_dict)` — appends one row to the ledger. Generates a unique `bet_id`
(UUID). Never overwrites existing rows.

`log_result(bet_id, result, actual_score)` — updates the `result` and
`profit_loss` columns for a specific `bet_id`. Also updates `running_bankroll`
based on previous row's bankroll + this profit/loss.

`get_summary()` — returns a dict with: `total_bets`, `settled_bets`, `wins`,
`losses`, `total_staked`, `total_profit_loss`, `roi_pct`, `current_bankroll`

**Validation:** Run `initialise_ledger()`, log two dummy bets, log results for
both, then call `get_summary()` and print it. Read the CSV back and print it in
full. Delete the dummy rows and confirm the file returns to headers-only state.

---

### Stage 10 — run_weekly.py

**Task:** Build the single entry point `run_weekly.py`. This script should:

1. Print a timestamped run header
2. Call `fetch_results()` and `fetch_standings()` — print row counts on success
3. Call `fetch_fixtures()` — print fixtures found
4. Call `fetch_odds()` — print fixtures with odds
5. Call `compute_team_stats()` — print team count
6. Call `predict_all_fixtures()` — print fixture count
7. Call `find_value_bets()` — print count of value bets found
8. Call `generate_report()` — print confirmation and file path
9. Print a run summary: time elapsed, value bets found, next step reminder
   (`"Review reports/value_bets_latest.csv and log any bets you place using ledger/ledger.py"`)

All steps wrapped in try/except with clear error messages that name the failed
step. If any pipeline step fails, skip downstream steps that depend on it but
continue with independent steps where possible.

**Validation:** Do a dry run with mock/cached data if live API keys are not yet
configured. Confirm the full pipeline executes end to end and produces
`reports/value_bets_latest.csv`.

---

### Stage 11 — README.md

**Task:** Write a clear `README.md` covering:

- What the system does
- Setup instructions (clone repo, `pip install -r requirements.txt`, create `.env`
  with both API keys)
- How to run (`python run_weekly.py`)
- How to log a bet manually (code snippet using `ledger.py`)
- How to log a result manually (code snippet)
- How to read your P&L summary (code snippet)
- CSV schema reference for all files
- Notes on model limitations and responsible use

---

## Future stages — do not build yet, listed for awareness

- **Stage 12:** Automated agent that places bets via bookmaker API
- **Stage 13:** Dashboard (e.g. Streamlit) showing ledger P&L, ROI curve, model
  calibration chart
- **Stage 14:** Multi-league support (Champions League, Championship, La Liga)
- **Stage 15:** Model improvement — Dixon-Coles correction, xG data integration,
  form weighting

---

## Reminder on validation

After every file is written, before moving to the next stage:

- Run the relevant function
- Print CSV shape, columns, and sample rows
- Confirm no unexpected nulls
- Confirm data types are correct (dates as datetime, numerics as float/int)
- Only then say "Stage X complete — ready for Stage Y"
