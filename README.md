# SBM — NFL + CFB research, Predictions, and 2026 Journal

A local research tool that prices NFL and FBS **spreads, moneylines, and totals**. It never places a sportsbook wager. You log real 2026 tickets in **Journal**. **Research** is one football week at a time, model vs market. **Predictions** is your current-year W/L take on NFL and P4 CFB. **Records** ranks each group from games already final.

## Surfaces

| Surface | What it is | Store |
| --- | --- | --- |
| **Research** | One Tuesday–Monday week, shared by NFL and CFB. Condensed cards, heatmap order, local kickoff clocks. Empty slots for published 2026 title and playoff times. Open a game to log a ticket. | Elo from `data/raw/` |
| **Game** | One matchup. Three model prices, then each real meeting in that season, with Log buttons. | Elo and unit stats from `data/raw/` |
| **Predictions** | Current-year schedule W/L takes (NFL + B1G/SEC/ACC/Big 12). Results fill in; picks never auto-flip. | `data/predictions/{season}.json` |
| **Ratings** | Neutral-field favorability versus an average opponent. | Elo from `data/raw/` |
| **Rankings** | Your order of NFL and each Power conference. Research shows it beside the model. | `data/rankings/{season}.json` |
| **Records** | Overall and conference record from ingested finals. Win percentage, then head-to-head, conference record, point differential, points scored. Not the official standings. | Finals in `data/raw/` |
| **Journal** | What you actually bet in 2026 (Novig today): dollars, parlays, early cash-out, year hit/miss | `data/journal/tickets.jsonl` |

`sbm simulate backtest` is a buried historical lab. It is not a weekly book. 2026 stays **hands-off** for historical P&L.

## Weekly playbook

1. `sbm ingest` if the slate looks stale.
2. Open **Research** (`/` or `/research`). Pick the week. Green, then yellow, then orange cards come first. Search a team, then open a game to log a real ticket into Journal. Weeks with no closing line still list the games. Championship and playoff weeks show empty slots until the matchups exist.
3. **Predictions** (`/predictions`): click remaining winners. **Rankings** (`/rankings`) is your order; paste a list in chat and the agent can apply it. CFB non-conference leftovers stay flagged for a gut call.
4. **Records** (`/records`): overall and conference record from finals already ingested. This is not the league’s tiebreaker sheet.
5. **Journal** (`/journal`): search and filter the book. After games, `sbm journal settle`.

**A few times a year**

```bash
sbm simulate backtest   # warmup 2015-2020, paper 2021-2025, skip 2026
```

## Research colors

The week is ordered by these fills, then by the best expected value on the card. A game with no posted line sits at the bottom. A game that is already final has no fill, no warning badge, and no You/Model ranks — those marks are for games still open. Warning is a red badge/border, not a fill. Fill is disagreement with the market:

- **Orange** — your predicted winner is not the market favorite
- **Yellow** — the model has a ticket
- **Green** — both
- **Red chip** — noisy `|edge| > 8`, early-season CFB (week < 4), or international NFL

Totals use yellow/green from the model only. Missing predictions are not a fade.

## Honesty rules

- Ratings update only **after** a game is predicted. No random train/test splits.
- Historical simulation evaluates against **closing** lines.
- CFB paper scoring starts at **Week 4** (Elo still updates from Week 1).
- Report research **units and ROI after −110**, not raw accuracy. Journal reports **dollars**.
- Same research windows for **NFL and CFB**: warmup **2015–2020** (ratings only), search **2021–2023**, holdout **2024–2025**, **2026 hands-off** for historical P&L.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Add a free [CollegeFootballData](https://collegefootballdata.com/) key to `.env` as `CFBD_API_KEY` if you want CFB ingest. NFL data is the public [nflverse](https://github.com/nflverse/nfldata) schedule CSV (no API key).

```bash
sbm ingest --league nfl --start 2015 --end 2026
sbm ingest --league cfb --start 2015 --end 2026   # needs CFBD_API_KEY
```

## Research CLI (buried lab)

```bash
sbm simulate bake-sample
sbm simulate backtest   # → data/simulation/historical_ledger.jsonl
sbm simulate picks      # prints the model slate (does not write Journal)
```

## Predictions

```bash
sbm predictions init
sbm predictions sync
sbm predictions set --game-id 2026_04_BUF_KC --winner BUF
```

Power-rank fill is not a dashboard form. Paste an ordered list in chat; the agent applies it (existing clicks stay). CFB non-conference games stay leftover.

## Journal

```bash
sbm journal seed-novig   # load recorded 2026 Novig tickets (idempotent)
sbm journal year
sbm journal settle
sbm journal add --stake 5 --implied 0.49 --team USC --opponent ORE --market moneyline --league cfb
sbm journal cashout TICKET_ID --amount 8.09
```

Championship futures are not tracked.

## Dashboard

```bash
sbm serve                 # 127.0.0.1:8000, no reload
sbm serve --reload        # pick up Python edits
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) (Research). **Game** is `/game`. **Predictions** is `/predictions`. **Ratings** is `/ratings`. **Rankings** is `/rankings`. **Records** is `/records`. **Journal** is `/journal`. Kickoff clocks render in the browser’s local time zone. Week labels stay calendar dates.

Ingest of a season range **merges** into the existing JSONL: only those seasons are replaced.

## Sample backtest (toy league)

Checked-in artifacts from `sbm simulate bake-sample` (not 2026 tickets):

- [`reports/sample/summary.json`](reports/sample/summary.json)
- [`reports/sample/picks.csv`](reports/sample/picks.csv)
- [`reports/sample/bankroll.png`](reports/sample/bankroll.png)

## Model (v1)

- Season-to-season **Elo** with mean-reversion (stronger for CFB), home-field, NFL rest.
- Separate **offensive/defensive scoring ratings** for totals.
- Margin → win probability with a normal CDF.
- Edges: 1.5 points on spread/total; moneyline EV ≥ 3% after juice.

No gradient boosting until this baseline is calibrated. No in-app LLM.

## Tests

```bash
pytest -q
ruff check src tests
```

CI runs the same on every push (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Docker (local stand-in for cloud)

```bash
cp .env.example .env
docker compose up --build
```

- Persist `data/simulation`, `data/journal`, `data/predictions`, and `data/raw` as volumes.
- Pass `CFBD_API_KEY` as an env var; never bake it into the image.

v1 does **not** provision a paid host.

## Project layout

- `src/sbm/models/` — Elo, totals, combined engine
- `src/sbm/data/` — NFL / CFB adapters + JSONL store
- `src/sbm/backtest.py` — walk-forward + current-week slate
- `src/sbm/paper.py` — historical simulation ledger only
- `src/sbm/journal.py` — real 2026 tickets and Tuesday–Monday windows
- `src/sbm/predictions.py` — current-year W/L takes
- `src/sbm/records.py` — standings from ingested finals
- `src/sbm/postseason.py` — published 2026 title and playoff times, not games
- `src/sbm/providers/lines.py` — swappable market lines
- `src/sbm/web/` — FastAPI + Jinja dashboard
- `tests/` — EV math, leakage, ledger isolation, journal grade, predictions

## Disclaimer

This is educational software. Sports betting involves risk. Past results do not imply future profit. The authors do not place bets for you.
