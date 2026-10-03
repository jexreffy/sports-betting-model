# Agent instructions (SBM)

This repo is **jexreffy’s personal NFL + CFB lab**. He goes by **jexreffy**. You implement in the code; do not stop at advice when he asked for a change.

As of **2026-10-03** this tree lives on an **M1 Max** that is now the low-spec weekly box. Older Cursor chats on the previous machine are gone. Read this file, `README.md`, and `BACKLOG.md` before changing behavior.

## What this is

A local research tool. It prices NFL and FBS spreads, moneylines, and totals from ingested closing lines. **Board** is one Tuesday–Monday week. **Journal** is real 2026 tickets (Novig today). **Predictions** is his current-year W/L take. **Rankings** is his order. **Records** is standings from ingested finals.

It **never places a sportsbook wager**. Do not add auto-bet, scrape a book to fire, or “sync Novig.” Logging and research only.

## Hard rules

- **Simulation vs Journal never mix.** Historical paper lives under `data/simulation/`. Real tickets live in `data/journal/tickets.jsonl`. Do not write 2026 money into a backtest ledger.
- **2026 is hands-off for historical P&L.** Warmup 2015–2020, search 2021–2023, holdout 2024–2025. Do not fit `LeagueParams` on 2026. `sbm simulate backtest` / `tune` already refuse the hands-off year.
- **Do not invent domain science.** Elo, edges, windows, and Board colors are already chosen. Implement what the project already does.
- **Lines are close only.** nflverse (NFL) and CFBD (CFB). There is no live-odds engine. `THE_ODDS_API_KEY` is a stub. Closing-line ingest is enough for the weekly loop.
- **Championship futures are not tracked.**
- **Python 3.11+** in `src/sbm/`. Thin CLI and FastAPI. Style: `X | None`, Ruff `E`, `F`, `I`, `UP`.
- **PR gate is `pytest -q` and `ruff check src tests`.** That suite is the gate — not a future AI QA bot.
- Treat **`main` as protected.** Never commit, merge, rebase onto, or push it. Branch → commit on the branch → review → PR. When he says the feature is complete and ready for PR: green suite, then Bugbot on the branch diff, green suite again if you edited, then `gh pr create`. **Never approve or merge.** He does that.
- Never commit `.env`, `data/raw/`, `data/simulation/`, `data/live/`, `data/journal/`, or `.venv/`.

## Data lives in this folder

`SBM_DATA_DIR` is relative `data` → `<repo>/data`. There is no `~/Library` or `~/.cache` store for SBM.

A `git clone` is **not** a move. The money and the slate are gitignored:

| Path | What |
| --- | --- |
| `.env` | `CFBD_API_KEY` (required for CFB ingest) |
| `data/raw/` | Games + units |
| `data/journal/` | Novig tickets |
| `data/predictions/`, `data/rankings/` | His takes and order |
| `data/simulation/`, `data/live/` | Research / legacy; do not mix with Journal |

On this M1 Max, recreate the venv if the copied one is the wrong arch:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Serve: `sbm serve` → `127.0.0.1:8000`. `--reload` when editing Python.

## Weekly loop (what he actually does)

1. `sbm ingest` (often `--start 2026 --end 2026`) if Board looks stale. Ingest **merges**: only the requested seasons are replaced.
2. Open Board (`/` or `/board`). Filter **NFL**, a **Power 4** conference (B1G, SEC, ACC, Big 12), or all CFB. A conference filter includes that team’s **non-conference** games. Championship slots stay conference-only.
3. Last week’s **model** miss sits above the cards. That is not Journal P&L.
4. Open a game to log a ticket. After finals, `sbm journal settle`. If he says there were no tickets on those games, do not invent settles.
5. Predictions: click winners; leftover CFB non-conference stays a gut call. Rankings: he pastes an ordered list in chat; apply it without wiping existing clicks. **Reconsider** / **I've reconsidered** are defined in the README — do not invent new pin rules.
6. A few times a year, buried lab: `sbm simulate backtest` (skips 2026).

Display labels (NFL, Big 12, Moneyline) are for the UI. Stored tokens stay `nfl`, `open`, `straight`, `moneyline`, etc.

## Product decisions already made

- **Board** replaced the Research tab. `/` and `/research` redirect to `/board` and keep query params. Simulation is not a weekly product surface.
- **P4 filters** (PR [#13](https://github.com/jexreffy/sports-betting-model/pull/13), after Board copy [#12](https://github.com/jexreffy/sports-betting-model/pull/12)): scope is “either team’s conference,” so a B1G team at a G5 still shows on B1G. Unlinked CFB journal legs resolve P4 via team-token match (`FLA`, `MISS`, `HOU`, …), not abbreviation-only.
- **You vs the model is not a bankroll.** Card colors are fade language, not a staking system. See README “Board colors.”
- **No gradient boosting** until this Elo baseline is calibrated. **No in-app LLM.**
- Offseason work waits until **2026 is final** (target March 2027): ingest leftovers, tune on 2021–23 / confirm 2024–25, then maybe slide `ResearchWindows` so 2027 is `hands_off`. Suggested knobs are never applied automatically.

## History the new agent would not otherwise have (through 2026-10-03)

This is operator memory from the previous machine, not a license to change the model.

- **Use:** weekly 2026 real bets. He logs what he actually took. You research, ingest, settle, and ship small PRs. You do not place the wager.
- **Florida at Missouri** (`cfb-401856708`, ~late Sep 2026): close was about Florida −4.5 / 56.5; the model swung hard to Missouri (about MIZ −6.3 / 61.5, ~65% MIZ). Public / Novig was Florida −5 to −5.5. He agreed Florida was the better side (Sumrall / Ole Miss context) but treated a letdown as possible; he would only take Missouri at something like −7 / +7. **He sat.** Do not treat that game as a “model was right, should have bet” lesson. Noisy early-season CFB is already a red-chip case.
- **Tyler Shoemaker / TSI:** a paid 2027 *overlay* idea, not an SBM line source. The marketplace he meant is **JuiceReel**. If it ever happens: optional second opinion on the board, **do not sync Novig**, **do not train Elo on TSI**. Not built. Fine as a Later/Not-now backlog item after 2026.
- **Yahoo-fantasy D+ / “why sell picks”:** his frame for paid sheets — they can be loud and still not a reason to override his sit. Do not add a “sell the slate” feature.
- **Ingest after MNF (week of the handoff):** 2026 refresh wrote on the order of 272 NFL / 888 CFB games. PHI@CHI finished 7–27; LA@DEN 26–30. He had **no tickets on those remaining games**, so there was nothing to settle from that slate. Journal at that snapshot: 29 tickets, 6 still open, about −$4 / ROI −0.035. The six opens were **later-week** games, not leftover MNF. Re-ingest and `sbm journal year` before quoting current P&L; those numbers age.
- **Move to this box:** copy the whole project folder (including gitignored `data/` and `.env`). Then new venv on ARM. Relative `data` only works if you run from the repo root.

## How to work

- Small, focused changes. One job per PR. Name things for the next reader.
- Non-trivial logic gets a test. Do not leave broken tests.
- Prefer patterns already in the repo. No drive-by refactors or extra files.
- Tokens over magic numbers.
- If he asks for a ranking paste or a ticket log, do the write. If he asks for a take, give the take and stop — do not “helpfully” place or settle.

## Not now (do not start)

Live play-by-play, Odds API as the live line, props as first-class auto-grade markets, championship futures, auto-betting, in-app LLM, auto-flipping remaining Predictions from the heatmap, mixing Journal dollars into simulation ROI.
