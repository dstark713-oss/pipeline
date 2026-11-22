# 00_refresh_ds: Dataset Refresh

Last updated: 2026-11-23

## Purpose

Refresh the local MOEX daily-bar dataset, rebuild corporate-action-adjusted data, and regenerate the point-in-time TOP50 membership/panel.

This is a dataset maintenance process. It is not the future instrument-state screener and does not generate trading signals or portfolio weights.

## Current implementation

The current implementation is:

`scripts/dataset/fresh/refresh_pipeline.py`

There is not yet a separate `scripts/tools/00_refresh_ds.py` launcher. The name `00_refresh_ds` is the documentation/tool label, not a claim that a wrapper file already exists.

Run from the repository root:

```powershell
python scripts/dataset/fresh/refresh_pipeline.py
```

## Inputs

- `data/interim/historical_universe/universe_common_shares.csv`
- `data/interim/historical_universe/universe_board_history.csv`
- `data/raw/moex_daily_raw.sqlite`
- Downloader implementation: `scripts/dataset/02_download_daily_bars_sqlite.py`

Only TQBR and EQBR board pairs are considered.

## Process

1. Read the historical common-share universe and board-history table.
2. Build eligible SECID/BOARDID pairs for TQBR/EQBR.
3. For each pair with existing raw observations, start after the last checked/observed date.
4. Request MOEX ISS history through the previous calendar day.
5. Compare incoming row hashes against existing SECID/BOARDID/TRADEDATE observations.
6. Skip identical existing rows; stop on a conflicting revision. Append only new rows.
7. Persist progress in `data/interim/fresh/fresh_state.sqlite`.
8. If all board downloads succeed, rebuild:
   - `data/processed/moex_daily_adjusted.sqlite` via `scripts/dataset/04_build_adjusted_dataset.py`
   - PIT TOP50 membership/panel via `scripts/dataset/05_build_top50_panel.py`
9. Write summary and errors to `data/interim/fresh/`.

## Safety properties

- Raw observations are append-only.
- Existing raw rows are never updated or deleted.
- Identical observations are not duplicated.
- Conflicting revisions are not silently accepted.
- Failed downloads prevent adjusted/panel rebuild.
- Derived datasets are rebuilt from raw/adjusted sources.
- No price forward-fill is performed.
- The current calendar day is not requested.

## Local outputs

- `data/interim/fresh/fresh_state.sqlite`: per-board refresh checkpoints.
- `data/interim/fresh/refresh_summary.json`: run status and counts.
- `data/interim/fresh/refresh_errors.csv`: per-board errors.
- `data/processed/moex_daily_adjusted.sqlite`: rebuilt adjusted database.
- `data/processed/top50/top50_membership.parquet`
- `data/processed/top50/top50_panel.parquet`

All of these are local data artifacts and must remain outside Git.

## Known limitations: do not mistake these for solved problems

- Pairs without existing raw observations are skipped. This script does not perform historical backfill or onboard all 1,167 historical common shares.
- The cutoff is the machine's calendar yesterday, not an explicit MOEX latest-completed-session lookup.
- A successful empty response advances the checkpoint through the cutoff. A late-published bar could therefore be missed; this needs a deliberate retry/reconciliation policy.
- Runtime validation of the current script has not yet been confirmed by the user.
- If a board fails after earlier pages were committed, those appended pages remain. Resolve the error and rerun; row hashes make repeated pages idempotent.
- A changed MOEX value for an existing key stops the run and requires manual correction review.

## First validation commands

From the repository root, run the syntax check first:

```powershell
python -m py_compile scripts/dataset/fresh/refresh_pipeline.py
```

Only after reviewing the local data backup and accepting a real API/database run:

```powershell
python scripts/dataset/fresh/refresh_pipeline.py
```

Review `refresh_summary.json`, `refresh_errors.csv`, raw latest dates/counts, adjusted row counts/integrity, and TOP50 panel validation.

## Future refinement

A small `scripts/tools/00_refresh_ds.py` wrapper may be added later if a stable user-facing entry point is useful. Do not create a duplicate implementation: it should only call the tested refresh pipeline. First validate the current implementation and resolve its coverage/checkpoint limitations.
