# SBM — NFL + CFB paper betting model

A local research tool that prices NFL and FBS college football **spreads, moneylines, and totals**, then tracks a **paper bankroll**. It never places a sportsbook wager.

This repo is a skills demo and a 2026 lab. Real-money bets stay outside the app. **Live mode** is a 2027-shaped board you can practice on now; it does not mix with simulation stats.

## Two modes, one model

| Mode | What it is | Ledger |
| --- | --- | --- |
| **Simulation** | Historical walk-forward replay, plus fake bets on **real current games** | `data/simulation/` |
| **Live** | The product you would open in 2027 (labeled *practice* until you flip a flag) | `data/live/` |

Ratings and EV math are shared. Ledgers cannot write across modes.

```
ingest (nflverse / CFBD)
        │
        ▼
  Elo + scoring ratings ──► edge vs market
        │
   ┌────┴────┐
   ▼         ▼
simulation  live     (isolated books)
   │         │
   └── FastAPI dashboard + CLI
```

## Honesty rules

- Ratings update only **after** a game is predicted. No random train/test splits.
- Historical simulation evaluates against **closing** lines.
- CFB paper scoring starts at **Week 4** (Elo still updates from Week 1).
- Report **units and ROI after −110**, not raw accuracy.
- 2026 real bets are independent of this app.
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

## Simulation

```bash
# Frozen toy artifacts (also used in this README)
sbm simulate bake-sample

# Honest walk-forward on ingested history → simulation ledger
sbm simulate backtest   # warmup 2015-2020, paper 2021-2025, skip 2026

# Paper this week's real games
sbm simulate picks
sbm simulate settle
```

## Live (practice)

```bash
sbm live picks
sbm live settle
```

`SBM_LIVE_PRACTICE=true` (default) labels the UI as a rehearsal. Set it to `false` when you actually try the 2027 workflow.

Odds today come from ingested nflverse/CFBD closes via a `LineProvider` protocol. [`TheOddsApiProvider`](src/sbm/providers/lines.py) is a stub so a later Odds API key is a data change, not a rewrite.

## Dashboard

```bash
sbm serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Use the **simulation | live** switch. Each mode shows its own weekly board, bankroll curve, and calibration-ish Brier.

## Sample backtest (toy league)

Checked-in artifacts from `sbm simulate bake-sample` (not live 2026 picks):

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

That is the same HTTP service you would put on Cloud Run, Fly.io, or Railway later:

- One container serves FastAPI (`sbm serve`).
- Persist `data/simulation` and `data/live` as two volumes (already in Compose).
- Pass `CFBD_API_KEY` as an env var; never bake it into the image.
- Schedule `sbm ingest` and `sbm simulate settle` / `sbm live settle` weekly (Cloud Scheduler, Fly cron, or the optional Compose `worker` profile).

v1 does **not** provision a paid host.

## Project layout

- `src/sbm/models/` — Elo, totals, combined engine
- `src/sbm/data/` — NFL / CFB adapters + JSONL store
- `src/sbm/backtest.py` — walk-forward + current-week slate
- `src/sbm/paper.py` — mode-keyed ledger
- `src/sbm/providers/lines.py` — swappable market lines
- `src/sbm/web/` — FastAPI + Jinja dashboard
- `tests/` — EV math, leakage, ledger isolation, parsers

## Disclaimer

This is educational software. Sports betting involves risk. Past paper results do not imply future profit. The authors do not place bets for you.
