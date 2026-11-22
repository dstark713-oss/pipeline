# Pipeline project context

Last updated: 2026-11-23

## Purpose

Build a reproducible MOEX daily market-data pipeline for a point-in-time TOP50-by-turnover research panel covering 2005 through the latest available trading date.

The GitHub repository `dstark713-oss/pipeline` is the source of truth for pipeline architecture and non-code project context. Local market data and generated databases/reports remain outside Git.

## Methodology invariants

- Historical universe discovery is complete. Do not rebuild it without a concrete defect.
- Raw MOEX observations are immutable. Every downstream dataset is separate.
- TOP50 membership is point-in-time: for date T, rank securities using rolling 60 trading sessions with a one-session lag. Information from T must not influence membership for T.
- 2004 is a warm-up year; the final historical panel begins in 2005.
- Never choose TOP50 once using the full history and backfill that membership into earlier dates.
- Do not forward-fill prices or manufacture missing bars.
- Do not automatically repair OHLC violations or delete plausible real return jumps.
- Unconfirmed corporate actions must not be applied.
- Preserve SECID and BOARDID. Do not blindly sum TQBR and EQBR observations.
- Listing history and observed daily trading activity are different concepts.
- Historical identity changes and ticker reuse require separate treatment.
- Historical and daily refresh calculations must use the same ranking implementation.

## Completed stages

### 1. Historical universe

Source: MOEX ISS historical shares listing plus security metadata.

Result:
- Listing board rows: 5,784
- Unique SECIDs: 2,526
- Common shares included: 1,167
- Other security types excluded: 1,359
- Quarantined due to missing metadata: 0
- Date range in source: 1997-03-24 through 2026-11-22

Local outputs:
- `data/interim/historical_universe/universe_common_shares.csv`
- `data/interim/historical_universe/universe_board_history.csv`

Important limitation: `history_from/history_till` are observed data-availability bounds, not legal listing intervals. Listing membership does not prove daily trading activity.

### 2. Raw daily history

Local SQLite:
- `data/raw/moex_daily_raw.sqlite`
- Source table: `daily_bars_raw`
- Download task table: `download_jobs`

Last confirmed snapshot:
- 728,550 raw rows
- 415 unique securities
- 2 boards: TQBR and EQBR
- Date range: 2004-01-05 through 2026-11-20
- 3,235 download jobs reported complete

The 415 securities observed in raw history are not automatically a completeness failure against the 1,167-member historical universe. Coverage must be interpreted using actual available history and download eligibility.

### 3. Raw database audit

Script authored locally:
- `scripts/dataset/03_audit_raw_database.py`

Default input:
- `data/raw/moex_daily_raw.sqlite`

Reports:
- `data/interim/raw_database_audit/`

Latest run:
- Raw rows: 728,550
- Rows processed: 728,550
- Unique securities: 415
- Unique boards: 2
- Observed market dates: 5,749
- Duplicate SECID/date groups: 1,322
- Cross-board overlaps: 1,322
- Cross-board mismatches: 1,322
- Incomplete history heuristic flags: 20
- Date gap intervals: 28
- Quality flag rows: 202,962, consisting only of zero_trades and zero_volume
- Raw database modified: NO

The overlap/quality investigation and cleaning decisions were already performed in the research2 workflow. Do not restart the forensic audit or invent a new TQBR/EQBR precedence rule. Reuse the established cleaning logic when transferring the downstream dataset workflow. The current adjusted-builder stage preserves source rows/boards one-to-one; any already-approved board resolution/cleaning must be applied at the appropriate downstream stage, not silently improvised here.

## Current stage: adjusted dataset

Next script:
- `scripts/dataset/04_build_adjusted_dataset.py`

Input:
- `data/raw/moex_daily_raw.sqlite`

Output:
- `data/processed/moex_daily_adjusted.sqlite`
- Table: `adjusted_daily_bars`

Reports:
- `data/interim/corporate_actions/`

The builder is adapted from the established research2 implementation:
- `research2/scripts/build_adjusted_daily_bars.py`

Confirmed corporate-action register carried over:
- VTBR consolidation 5000:1, effective 2024-07-15
- IRAO consolidation 100:1, effective 2015-01-20
- GMKN split 1:100, effective 2024-04-08
- ROLO split 1:10, effective 2023-01-19
- GEMA split 1:10, effective 2024-02-08
- PLZL split 1:10, effective 2025-03-27
- BELU additional share distribution 1:8, effective 2024-08-22; effective-date OHLC is quarantined due to mixed price scales

Adjustment convention:
- Historical prices are divided by new_shares_per_old_share.
- Historical share volume is multiplied by new_shares_per_old_share.
- The effective date is the first bar in the new native scale.
- Raw remains read-only.
- No automatic outlier removal or forward-fill.
- Chained actions for one SECID require explicit logic and are not silently composed.

Important: validate the adapted script against the local raw DB before proceeding. Confirm source/target row counts, SQLite integrity, adjustment counts by action, and BELU quarantine. Do not claim execution success before the user runs it.

## Planned stages

1. Build and validate adjusted dataset.
2. Apply the established cleaning/board-resolution logic and build the point-in-time rolling 60-session TOP50 ranking.
3. Build the historical panel from the same ranking engine that will be used by daily refresh.
4. Implement daily raw refresher from scratch: discover latest available MOEX session, download missing bars for the eligible universe, persist checkpoints, retries and idempotent progress.
5. Implement daily adjusted updater.
6. Implement daily ranking and panel updater; publish current active TOP50 list and update the historical panel.
7. Add run logs, failure reports, integrity checks and safe recovery/replay.

## Daily refresher design constraints

- Download the eligible historical universe, not only today's TOP50. A current non-member can enter TOP50 later.
- Incremental download must be resumable and idempotent.
- Never mutate raw observations in place.
- Do not publish a new panel if upstream download/adjustment/validation fails.
- Keep a last-successful build and use atomic replacement/versioned outputs.
- Historical backfill and daily refresh must call the same ranking code.
- The current active list must be calculated from the latest fully available trading session, not from an incomplete intraday snapshot.

## Repository hygiene

Do not commit:
- `data/` contents
- SQLite databases
- CSV raw/intermediate data exports
- Parquet datasets
- logs, caches, temporary/building files

Commit code, documentation, schemas and small deterministic tests only.

## Working style

- Prefer complete runnable files over instructions to edit scattered fragments.
- Every Python script starts with a comment containing its path and filename.
- Do not rewrite settled methodology without identifying a concrete defect.
- Be explicit about what was inspected, what was inferred, and what has not yet been run.
