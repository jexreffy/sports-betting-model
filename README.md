# SBM — NFL + CFB research model + 2026 Journal

A local research tool that prices NFL and FBS **spreads, moneylines, and totals**. It never places a sportsbook wager. You log real 2026 tickets in **Journal**; **Research** (Simulation) is the model’s price sheet and historical lab.

## Two books

| Book | What it is | Store |
| --- | --- | --- |
| **Research (Simulation)** | Walk-forward backtest, later tune, and this week’s **model slate**. Not your money. Look, don’t book. | `data/simulation/historical_ledger.jsonl` (backtest). Weekly paper `ledger.jsonl` is not the product. |
| **Journal** | What you actually bet in 2026 (Novig today): dollars, parlays, early cash-out, year hit/miss | `data/journal/tickets.jsonl` |

Ledgers cannot write across books. 2026 is still **hands-off** for historical P&L.

## Weekly playbook

**While you bet**

1. `sbm ingest` if the slate looks stale.
2. Open **Research** (`/research`). Read model tickets and edges. Do not fill a paper bankroll there — it does not train Elo.
3. Bet at Novig (or anywhere) however you actually play.
4. Log that ticket on **Journal** (`/` or `/journal`): sportsbook, dollars, odds, legs.

**After games (leave MNF open until it is final)**

1. `sbm ingest`
2. `sbm journal settle`
3. Optional: glance at Research vs Journal if you faded the model. That is a personal scorecard, not training.

**A few times a year**

```bash
sbm simulate backtest   # warmup 2015-2020, paper 2021-2025, skip 2026
```

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

## Research (Simulation)

```bash
sbm simulate bake-sample
sbm simulate backtest   # → data/simulation/historical_ledger.jsonl
sbm simulate picks      # prints / optionally papers the model slate (not Journal)
sbm simulate settle     # grades leftover paper diary rows only
```

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

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) (Journal). **Research** is `/research`.

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

No gradient boosting until this baseline is calibrated.

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

- Persist `data/simulation` and `data/journal` as two volumes.
- Pass `CFBD_API_KEY` as an env var; never bake it into the image.

v1 does **not** provision a paid host.

## Project layout

- `src/sbm/models/` — Elo, totals, combined engine
- `src/sbm/data/` — NFL / CFB adapters + JSONL store
- `src/sbm/backtest.py` — walk-forward + current-week slate
- `src/sbm/paper.py` — simulation paper ledger
- `src/sbm/journal.py` — real 2026 tickets
- `src/sbm/providers/lines.py` — swappable market lines
- `src/sbm/web/` — FastAPI + Jinja dashboard
- `tests/` — EV math, leakage, ledger isolation, journal grade

## Disclaimer

This is educational software. Sports betting involves risk. Past results do not imply future profit. The authors do not place bets for you.
