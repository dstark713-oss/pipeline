# Dataset scripts

Scripts for universe construction, historical raw data collection, auditing, transformations, and panel construction will live here. Each script should state its path, purpose, input assumptions, outputs, and resumability behavior in its header.

## Incomplete daily-bar repair

`06_repair_incomplete_bars.py` is a standalone repair utility. It does not modify the raw SQLite database and does not change the refresh process.

It selects distinct SECID/BOARDID/TRADEDATE keys in `daily_bars_raw` where at least one OHLC field is NULL, requests the exact daily candle from MOEX ISS `/candles.json`, validates that all OHLC values are present and internally consistent, and stores valid corrections in:

`data/interim/bar_repairs/moex_candle_repairs.sqlite`

The overlay stores source endpoint, original raw row hashes, source payload, fetch timestamp, and a deterministic repair ID. It is separate from the append-only raw database.

Run from the repository root:

```powershell
python scripts/dataset/06_repair_incomplete_bars.py --dry-run --limit 10
python scripts/dataset/06_repair_incomplete_bars.py
python scripts/dataset/04_build_adjusted_dataset.py
```

The first command is a small network smoke test and writes no repair rows. The second downloads and stores all valid repairs. The adjusted builder then applies overlay values at build time and records `bar_repair_id` and `bar_repair_fetched_at_utc` in the derived adjusted table. Re-running the repair utility updates the overlay only when the returned candle values change.

The utility writes a compact report to `data/interim/bar_repairs/repair_report.json`. Unavailable, incomplete, or invalid MOEX candles are reported and are not written to the overlay. No forward-fill, synthetic bar, or raw-row mutation is performed.

Unit tests:

```powershell
python -m unittest discover -s scripts/dataset/tests -v
```
