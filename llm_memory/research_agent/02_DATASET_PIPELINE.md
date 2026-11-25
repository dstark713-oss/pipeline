# Dataset Pipeline: Architecture and State

Last updated: 2026-11-23

## Objective

Build a reproducible point-in-time TOP50 panel by turnover for MOEX common shares, covering 2005 through the latest fully available trading date. The panel is intended as a stable research substrate and future agent input.

## Methodology invariants

- Historical TOP50 membership is calculated separately for every date.
- Ranking uses rolling 60 market sessions of turnover, shifted by one session. Information from date T must not influence membership on T.
- 2004 is a warm-up year; final panel starts in 2005.
- Never select TOP50 once using the full sample and backfill it into earlier dates.
- Preserve raw MOEX observations. Raw SQLite is append-only; do not update/delete existing observations.
- Keep raw, adjusted, and panel datasets separate.
- No forward-fill of prices and no synthetic missing bars.
- Record OHLC violations; do not auto-correct them.
- Preserve plausible real return jumps; do not automatically delete outliers.
- Apply only confirmed corporate actions. Unconfirmed actions stay unadjusted.
- Preserve SECID and BOARDID at the raw/adjusted stages.
- Do not blindly sum TQBR and EQBR OHLC. Activity aggregation and price-board selection are separate decisions.
- Listing membership is not proof of daily trading activity.
- `history_from/history_till` are observed data-availability bounds, not legal listing intervals.
- Ticker reuse / issuer identity changes require explicit review.
- Historical build and daily refresh must use the same ranking logic.

## Stage 1: Historical universe

**Status: user-reported complete.**

MOEX ISS sources:
- `https://iss.moex.com/iss/history/engines/stock/markets/shares/listing`
- `https://iss.moex.com/iss/securities/{SECID}`

Last reported result:
- Source date range: 1997-03-24 to 2026-11-22
- Listing-board rows: 5,784
- Unique SECIDs: 2,526
- Common shares included: 1,167
- Other security types excluded: 1,359
- Quarantined for missing metadata: 0

Local outputs (not committed):
- `data/interim/historical_universe/universe_common_shares.csv`
- `data/interim/historical_universe/universe_board_history.csv`

Inclusion policy: `TYPE == common_share`; other types excluded; missing/failed metadata would be quarantined. Do not rebuild this stage without a concrete defect.

## Stage 2: Raw daily history

**Status: user-reported complete for the scheduled jobs; not full-universe coverage.**

- Script: `scripts/dataset/02_download_daily_bars_sqlite.py`
- Database: `data/raw/moex_daily_raw.sqlite`
- Tables: `daily_bars_raw`, `download_jobs`
- Last reported snapshot: 728,550 rows; 415 SECIDs; dates 2004-01-05 to 2026-11-20; 3,235 jobs marked complete; boards TQBR and EQBR.

Important limitation: all created jobs being complete means those jobs finished. It does not prove that all 1,167 historical common shares have complete daily coverage. The 415 observed SECIDs must not be represented as complete coverage of the 1,167-member universe.

## Stage 3: Raw database audit

**Status: user-reported run completed; raw DB remained unchanged.**

Script: `scripts/dataset/03_audit_raw_database.py`

Last reported audit:
- 728,550 raw rows
- 1,322 duplicate SECID/date groups
- 1,322 cross-board overlaps
- 1,322 cross-board mismatches
- 20 incomplete-history heuristic flags
- 28 date-gap intervals
- 202,962 quality-flag rows
- EQBR: 46,008 rows; TQBR: 682,542 rows
- Flags: zero_trades 101,481; zero_volume 101,481

The user stated that board handling and cleaning decisions had already been worked through in `research2`. Do not restart that forensic work without a concrete reason. Reuse the approved board logic described below.

## Stage 4: Adjusted dataset

**Status: user-reported successful build.**

Script: `scripts/dataset/04_build_adjusted_dataset.py`

- Input: `data/raw/moex_daily_raw.sqlite`, opened read-only.
- Output: `data/processed/moex_daily_adjusted.sqlite`
- Table: `adjusted_daily_bars`
- One output row per source row; source board rows retained; no deduplication at this stage.

Corporate actions currently encoded:
- VTBR consolidation 5000:1, effective 2024-07-15.
- IRAO consolidation 100:1, effective 2015-01-20.
- GMKN split 1:100, effective 2024-04-08.
- ROLO split 1:10, effective 2023-01-19.
- GEMA split 1:10, effective 2024-02-08.
- PLZL split 1:10, effective 2025-03-27; official MOEX notice: https://www.moex.com/n88888
- BELU additional-share distribution 1:8, effective 2024-08-22; effective-date OHLC quarantined due to apparent mixed price scales.

User-reported output:
- Source/output rows: 728,550 / 728,550
- SQLite integrity: `ok`
- Status counts: UNADJUSTED_NO_ACTION 707,159; ADJUSTED 14,445; QUARANTINED_MIXED_SCALE 1; POST_ACTION_NATIVE_SCALE 6,945
- Raw database modified: false
- Forward-fill: false
- Automatic outlier removal: false
- Source rows preserved one-to-one: true
- Board rows preserved without deduplication: true

Adjustment convention: historical prices are multiplied by the inverse of `new_shares_per_old_share`; historical share volume is multiplied by the share factor. The effective date is treated as the first bar in the new native scale. Chained actions for one SECID require explicit implementation and must not be silently composed.

## Board handling carried from approved research2 implementation

Legacy reference:
- `research2/scripts/eda/00_build_eda_panel.py`
- `research2/scripts/eda/03_build_historical_universe.py`

Approved behavior:
- Turnover/value and adjusted volume are summed across TQBR and EQBR.
- OHLC is selected from one board, not summed.
- TQBR has priority; EQBR is fallback.
- The current pipeline's panel/primitive aggregation improves this by preferring a row with complete/valid OHLC first, then applying TQBR/EQBR priority.
- Aggregated SECID/date must be unique.
- Raw source observations remain intact.
- Exclude GAZC, GAZS, GAZT.
- Exclude the market suspension interval 2022-02-28 through 2022-03-23.
- Do not invent a universal TQBR/EQBR switchover date; historical overlaps exist.

## Stage 5: Point-in-time TOP50 panel

**Status: script exists in GitHub; panel build was previously reported complete.**

Script: `scripts/dataset/05_build_top50_panel.py`

Source: adjusted SQLite, read-only.

Outputs (local only):
- `data/processed/top50/top50_membership.parquet`
- `data/processed/top50/top50_panel.parquet`
- `data/interim/top50_build/summary.json`
- `data/interim/top50_build/daily_summary.csv`
- `data/interim/top50_build/board_aggregation_audit.csv`

Core logic:
- Volume and value sum across TQBR/EQBR.
- OHLC from a valid complete OHLC row first, then TQBR preference, then EQBR fallback.
- Exclusions: GAZC, GAZS, GAZT and 2022-02-28 through 2022-03-23.
- Calendar from distinct TQBR/EQBR trading dates, with suspension interval removed.
- Rolling 60-session turnover, shifted one session before ranking.
- Eligibility requires full 60-session exposure history.
- TOP50 per date from 2005-01-01 onward.
- Membership includes ranking_asof_date, value_60d, rank, universe_size, selection_method.
- A member can remain in membership with `bar_available=0`; no price forward-fill.
- Output is written only after validation.

Last user-provided panel shape:
- 203,053 rows in the last user-provided snapshot; the current EDA field contract is listed below.
- Dates: 2005-01-11 through 2026-11-20
- Known panel fields: tradedate, ranking_asof_date, secid, value_60d, rank, universe_size, selection_method, volume, value, n_boards, boards, adjusted_open, adjusted_high, adjusted_low, adjusted_close, price_board, adjustment_status, bar_available. The current EDA data contract does not include `numtrades`; do not assume a Number of Trades variable is available.

## Data flow

`MOEX ISS → historical universe → raw daily SQLite → adjusted daily SQLite → PIT TOP50 membership/panel → experiments → reviewed primitive pack → future state screener`

Raw observations and local generated data stay outside Git. The repository tracks code, context, and small deterministic tests only.
