# Next Step Improvements — Model Accuracy

This document lists statistical improvements that could make the Poisson model more accurate, ranked by expected impact. For each item: what it is, whether the data is attainable, where to get it, and whether the source is free.

---

## Priority 1 — High Impact

### 1. xG (Expected Goals) — used alongside actual goals

**What it is:** Expected Goals measures the quality of chances created — how many goals a team *should* have scored based on shot position, type, and difficulty. Rather than replacing actual goals, the model would use **both signals together**:

- **xG** captures chance creation and defensive solidity — it reflects the underlying quality of a team's play stripped of finishing luck
- **Actual goals** captures finishing ability and composure — a team consistently outscoring their xG is genuinely clinical, not just lucky

Blending the two gives a more complete picture than either alone. A team with high xG but low actual goals may be wasteful in front of goal; a team outscoring their xG significantly may be riding form that will regress. Using both features lets the model distinguish between these cases.

**Example:** Arsenal generate 2.1 xG per game but score 1.9 actual goals — slightly underperforming their chances but broadly consistent, suggesting a reliable rating. A team generating 1.0 xG but scoring 1.8 actual goals is likely overrated by a goals-only model and due to regress.

| | |
|---|---|
| **Attainable?** | Yes |
| **Source** | [Understat](https://understat.com) — covers Premier League, La Liga, Bundesliga, Serie A, Ligue 1, RFPL |
| **Access method** | `understat` Python package (pip install understat) — no API key required, scrapes directly |
| **Cost** | Free |
| **What changes in code** | `pipelines/fetch_stats.py` — add `fetch_xg()` function to pull xGH/xGA per match; `models/poisson_model.py` — blend xG and actual goals in `compute_team_stats()`, e.g. weighted average such as `(xG × 0.6) + (actual goals × 0.4)` |

> **Note:** This is already planned for the start of the 2026/27 season — see README. The blending weight (0.6/0.4 or similar) can be tuned once sufficient historical data is available to backtest against.

---

### 2. Shots on Target Ratio

**What it is:** The ratio of shots on target for vs against each team. A team generating 7 shots on target per game against an opponent generating 2 has a very different expected scoreline to what a goals-only model sees. Highly correlated with xG and available without needing to switch data source.

| | |
|---|---|
| **Attainable?** | Yes |
| **Source** | [football-data.org](https://www.football-data.org/) — already used in this project |
| **Access method** | Existing `FOOTBALL_DATA_API_KEY` — shots data is included in the match response object |
| **Cost** | Free (same free tier already in use) |
| **What changes in code** | `pipelines/fetch_stats.py` — add shot columns to `fetch_results()`; `models/poisson_model.py` — blend shots ratio into attack/defence ratings |

---

### 3. Injury and Suspension Data

**What it is:** Adjusts team ratings for confirmed absences. A team missing their first-choice striker and goalkeeper has materially different expected goals — potentially a 10-15 percentage point shift in outcome probabilities. Currently the model is completely blind to this.

| | |
|---|---|
| **Attainable?** | Partially |
| **Source (free)** | [football-data.org](https://www.football-data.org/) — includes squad and lineup data at the match level (post-match); some injury flags in team endpoints |
| **Source (better, paid)** | [API-Football](https://www.api-football.com/) via RapidAPI — includes pre-match injury lists, ~$10–15/month for Premier League coverage |
| **Source (free, manual)** | [Transfermarkt](https://www.transfermarkt.co.uk/) — detailed injury history, but requires scraping (grey area, terms of service dependent) |
| **Cost** | Free tier limited; full pre-match injury lists require ~$10–15/month |
| **Complexity** | High — requires mapping player names to team ratings and quantifying the impact of each player's absence |

> **Recommendation:** Start by pulling confirmed lineup data from football-data.org (free, already integrated) to detect when known key players are absent from the starting XI.

---

## Priority 2 — Medium Impact

### 4. Recent Form — Explicit Signal

**What it is:** The current exponential decay weighting already gives more weight to recent matches — but it does so gradually. An explicit "last 6 games" form metric would capture abrupt changes: a new manager appointment, a string of injuries, or a psychological collapse after a heavy defeat.

| | |
|---|---|
| **Attainable?** | Yes — no new data needed |
| **Source** | `data/raw/results_*.csv` — already collected |
| **Access method** | Code change only — filter to last N matches per team and compute a separate form rating |
| **Cost** | Free — uses existing data |
| **What changes in code** | `models/poisson_model.py` — add a form window (last 6 games) as a secondary rating signal alongside the full-season rating |

---

### 5. Head-to-Head History

**What it is:** Some fixtures have systematic patterns that the season-level model misses. Certain tactical matchups consistently produce low-scoring or high-scoring games regardless of general league form. H2H records over the last 3–5 seasons can act as a prior.

| | |
|---|---|
| **Attainable?** | Yes |
| **Source** | [football-data.org](https://www.football-data.org/) — historical seasons available via `competitions/{id}/matches?season=XXXX` |
| **Access method** | Existing `FOOTBALL_DATA_API_KEY` — pull 3–5 prior seasons |
| **Cost** | Free (same free tier) |
| **What changes in code** | `pipelines/fetch_stats.py` — add `fetch_historical_h2h()` function; `models/poisson_model.py` — blend H2H goal average into expected goals calculation |

---

### 6. Multi-Season Elo Ratings

**What it is:** The current model starts fresh each season, meaning newly promoted teams have only a few games of data before ratings stabilise. A multi-season Elo rating — where each team carries a skill score updated after every match across multiple seasons — provides a much stronger prior, especially in August and September.

| | |
|---|---|
| **Attainable?** | Yes |
| **Source (pre-computed)** | [ClubElo.com](http://clubelo.com/) — free, provides daily Elo ratings for all major European leagues via a simple CSV download endpoint |
| **Source (self-computed)** | football-data.org historical data (free) — can be used to compute your own Elo from scratch |
| **Access method** | ClubElo: HTTP GET `http://api.clubelo.com/{TeamName}` returns a CSV — no API key required |
| **Cost** | Free |
| **What changes in code** | `pipelines/fetch_stats.py` — add `fetch_elo_ratings()` using ClubElo API; `models/poisson_model.py` — use Elo as the prior for regression to mean instead of league average (1.0) |

---

### 7. Fixture Congestion / Rotation Risk

**What it is:** Teams playing European football on Thursday and Premier League on Sunday show measurable performance degradation. Similarly, teams in an FA Cup run mid-week often rotate squads for league games. This particularly affects BTTS and over/under 2.5 markets — rotated squads score fewer goals.

| | |
|---|---|
| **Attainable?** | Yes — no new data source needed |
| **Source** | football-data.org — fixture dates already fetched; cross-reference with UEFA/cup fixture calendars |
| **Access method** | `pipelines/fetch_fixtures.py` already pulls all scheduled matches — add logic to flag ≤4 days' rest since last match |
| **Cost** | Free |
| **What changes in code** | `models/poisson_model.py` — add a congestion multiplier that reduces expected goals for teams with short rest periods |

---

## Priority 3 — Refinements

### 8. Referee Tendencies

**What it is:** Some referees produce significantly more bookings, penalties, and added time than others. More penalties = more goals, affecting BTTS and over/under markets. A referee who averages 0.8 penalties per game versus 0.2 has a measurable impact on expected goals.

| | |
|---|---|
| **Attainable?** | Yes — data already being collected |
| **Source** | football-data.org — referee name is already present in the match results response |
| **Access method** | Existing `FOOTBALL_DATA_API_KEY` — add referee column to `fetch_results()` |
| **Cost** | Free |
| **What changes in code** | `pipelines/fetch_stats.py` — save referee column; `models/poisson_model.py` — compute per-referee average goals/penalties as a multiplier; `pipelines/fetch_fixtures.py` — pull appointed referee for upcoming matches |

---

### 9. Weather and Pitch Conditions

**What it is:** Heavy rain and strong wind measurably reduce goal output — particularly relevant for over/under 2.5 markets. Studies show matches played in rain produce on average 0.2–0.3 fewer goals than dry conditions. Wind above 30mph significantly impairs long passing and shooting accuracy.

| | |
|---|---|
| **Attainable?** | Yes |
| **Source** | [OpenWeatherMap API](https://openweathermap.org/api) — forecast endpoint covers 5 days ahead at hourly resolution |
| **Access method** | Free API key at openweathermap.org — `api.openweathermap.org/data/2.5/forecast?q={city}&appid={key}` |
| **Cost** | Free tier: 1,000 calls/day — more than sufficient for a weekly run covering ~10 fixtures |
| **What changes in code** | New `pipelines/fetch_weather.py`; `models/poisson_model.py` — apply a goals multiplier based on precipitation and wind speed for the fixture kick-off time and venue |

---

### 10. Set-Piece Threat

**What it is:** Teams with strong corner and free-kick routines consistently score goals that do not show up in open-play xG. Brentford are a well-known example. This affects BTTS and over/under markets — a team that scores 30% of its goals from set-pieces has a different goal distribution than their open-play stats suggest.

| | |
|---|---|
| **Attainable?** | Partially |
| **Source (free)** | [FBref](https://fbref.com) — detailed set-piece stats, but requires HTML scraping |
| **Source (structured, free)** | [StatsBomb Open Data](https://github.com/statsbomb/open-data) — event-level data including set-piece types, but mainly covers historical competitions |
| **Source (paid)** | Opta / Stats Perform — enterprise pricing, not realistic for this project |
| **Cost** | Free (scraping) — StatsBomb open data is fully free |
| **Complexity** | Medium-high — requires scraping and matching team names across sources |

---

### 11. Betting Market Line Movement

**What it is:** Tracking whether odds have shortened or drifted since the model last ran is a powerful signal. If a value bet was identified at 3.0 but the price has since moved to 2.5, professional money has moved against your position — the market has likely corrected. If it has drifted to 3.5, the model may be finding even more value.

| | |
|---|---|
| **Attainable?** | Partially |
| **Source** | [The Odds API](https://the-odds-api.com/) — already integrated; historical odds snapshots are a **paid feature** (Pro plan) |
| **Alternative** | Run `fetch_odds.py` twice (e.g. Monday and Friday) and compare — tracks movement using existing free tier |
| **Cost** | Free if using the dual-run approach; ~$50/month for full historical odds via The Odds API Pro |
| **What changes in code** | `pipelines/fetch_odds.py` — save timestamped snapshots; `analysis/value_detector.py` — flag bets where odds have moved against the model since the last run |

---

## Summary Table

| Improvement | Impact | Data Available? | Source | Free? |
|---|---|---|---|---|
| xG alongside actual goals | High | Yes | Understat (`understat` package) | Yes |
| Shots on target ratio | High | Yes | football-data.org (already integrated) | Yes |
| Injury / suspension data | High | Partial | football-data.org (limited) / API-Football (full) | Limited / ~£10/mo |
| Recent form signal | Medium | Yes | Existing results CSV — code change only | Yes |
| Head-to-head history | Medium | Yes | football-data.org historical seasons | Yes |
| Multi-season Elo ratings | Medium | Yes | ClubElo.com API | Yes |
| Fixture congestion | Medium | Yes | Existing fixture data — code change only | Yes |
| Referee tendencies | Low-Medium | Yes | football-data.org (already integrated) | Yes |
| Weather conditions | Low-Medium | Yes | OpenWeatherMap API | Yes (1,000 calls/day free) |
| Set-piece threat | Low-Medium | Partial | FBref (scraping) / StatsBomb open data | Yes (with scraping) |
| Betting line movement | Low-Medium | Partial | The Odds API (dual-run workaround) | Yes (workaround) |

---

## Recommended Implementation Order

1. **xG** — biggest accuracy gain, zero cost, already planned for 2026/27
2. **Shots on target** — same data source already in use, small code change
3. **Referee tendencies** — data already being collected, just not saved
4. **Fixture congestion** — no new data needed, purely a code change
5. **Multi-season Elo** — free ClubElo API, solves the early-season cold-start problem
6. **Head-to-head history** — same API key, adds historical context
7. **Weather** — free API, particularly valuable for over/under 2.5 market accuracy
8. **Injury data** — most impactful but most complex; start with football-data.org lineups
9. **Set-piece threat** — useful but requires scraping setup
10. **Line movement** — implement the dual-run workaround before considering paid tier
