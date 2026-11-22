# Daily Refresh Mechanism

Last updated: 2026-11-23

## Current implementation

GitHub file:
- `scripts/dataset/fresh/refresh_pipeline.py`

The script exists on `main`. It is the current refresh entry point for the dataset pipeline. There is no separate `scripts/tools/00_refresh_ds.py` wrapper in the inspected repository.

Command from the repository root:
```powershell
python scripts/dataset/fresh/refresh_pipeline.py
```

**Execution status:** code inspected in GitHub. The user has not yet supplied a successful local run result for this version. Treat it as unverified at runtime.

## Intended sequence

1. Read the historical common-share universe and board-history CSVs.
2. Build SECID/board pairs for TQBR and EQBR.
3. For pairs with existing raw observations, request data after the last checked/observed date through yesterday.
4. Use downloader helpers from `scripts/dataset/02_download_daily_bars_sqlite.py`.
5. Append new raw rows to `data/raw/moex_daily_raw.sqlite`.
6. Rebuild the adjusted SQLite dataset with `scripts/dataset/04_build_adjusted_dataset.py`.
7. Rebuild the PIT TOP50 panel with `scripts/dataset/05_build_top50_panel.py`.
8. Write summary/error reports under `data/interim/fresh/`.

## Safety behavior implemented in code

- Raw observations are not updated or deleted.
- Existing SECID/BOARDID/TRADEDATE rows are checked by row hash.
- Identical existing rows are skipped.
- If MOEX returns a changed hash for an existing key, the script raises a correction-review error instead of overwriting or adding a duplicate.
- Pages are committed as they are inserted; interrupted progress can be resumed.
- Refresh checkpoints live in a separate `data/interim/fresh/fresh_state.sqlite`.
- The current calendar day is not requested; cutoff is `date.today() - 1 day`.
- Failed board requests are recorded in `refresh_errors.csv`.
- If any download errors occur, adjusted/panel rebuild is skipped.
- Adjusted DB is rebuilt before panel; panel summary validation must exist and all validation values must be true.
- Summary is written atomically.
- No forward-fill is applied by the refresh script.

## Important limitations and risks to test

1. **Not a historical backfill tool.** If a SECID/board pair has no existing raw observations, it is skipped. Historical backfill remains stage 02.
2. **Coverage is not the entire 1,167-share universe.** The refresh only extends board pairs already represented in raw data; it does not onboard every missing security from the historical universe.
3. **Cutoff uses the machine's calendar yesterday, not an explicit MOEX latest-completed-session endpoint.** Check weekend/holiday and delayed-publication behavior.
4. **Empty response advances the checkpoint to the cutoff.** This avoids repeatedly requesting inactive securities, but could skip a late-published bar if MOEX data for a session appears after the first empty response. Test this behavior before treating it as production-safe.
5. **No full runtime validation is recorded.** Import helper signatures, schema assumptions, Windows behavior, API pagination, and full rebuild time still need a user-run test.
6. **A download error stops derived rebuild, but raw pages committed before the error remain appended.** This is intentional resumable behavior; inspect the error report and rerun after resolving the cause.
7. **A conflicting revised raw observation requires manual correction review.** Do not edit raw data in place; decide on an explicit correction/audit procedure separately.

## Suggested validation sequence

Run one command at a time from the repository root:

```powershell
python -m py_compile scripts/dataset/fresh/refresh_pipeline.py
```

Then, when ready for a real API/database run:

```powershell
python scripts/dataset/fresh/refresh_pipeline.py
```

After the run, inspect:
- `data/interim/fresh/refresh_summary.json`
- `data/interim/fresh/refresh_errors.csv`
- raw row count and latest date per board
- adjusted row count and SQLite integrity
- TOP50 panel end date, row count, and validation results

Do not run against production local data merely to test imports. Prefer a controlled copy/sandbox for destructive or uncertain tests. The script is designed to append raw rows and rebuild derived outputs, so preserve a backup before first full execution.

## Relationship to the future screener

This refresh mechanism updates the dataset. It is not the production state screener. The future screener is a separate deliverable and must wait until the primitive research is reviewed and the user approves the primitive pack.
