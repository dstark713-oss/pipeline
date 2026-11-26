# Aggressive Market Snapshot

Builds a historical per-ticker snapshot for the point-in-time TOP50 universe.

## Run

From the repository root:

```powershell
python scripts/one_use/aggressive_market_snapshot/build_market_snapshot.py
```

Optional coverage threshold for the daily equal-weight benchmark:

```powershell
python scripts/one_use/aggressive_market_snapshot/build_market_snapshot.py --min-benchmark-coverage 0.80
```

## Inputs

- `data/processed/top50/top50_membership.parquet`
- `data/processed/moex_daily_adjusted.sqlite`, table `adjusted_daily_bars`

The script reads the adjusted database in read-only mode. It uses the panel's existing PIT membership and does not rebuild or alter the panel.

## Benchmark definition

The benchmark is a daily rebalanced equal-weight portfolio of the PIT TOP50. Daily return on date t uses the constituents selected for t-1, avoiding use of same-day membership information. Returns are averaged over constituents with valid close-to-close returns. A daily benchmark return is retained only when valid-return coverage meets `--min-benchmark-coverage` (default 80%). Coverage and valid constituent counts are stored for diagnostics. Multi-session benchmark returns are compounded daily returns.

## Features

- Adjusted close returns: 1, 5, 10, 20 sessions
- Relative strength versus equal-weight PIT TOP50: 5, 10, 20 sessions
- Momentum acceleration: change in 5D and 10D returns versus the preceding non-overlapping window
- Annualized realized volatility: 20 and 60 sessions
- Drawdown from rolling 20D and 60D highs
- Current turnover versus trailing 20D median
- PIT rank, current bar availability, turnover and volume

No price forward-fill is applied. Rolling return and volatility features require complete observations over their stated windows.

## Outputs

Written locally under `data/interim/aggressive_market_snapshot/`:

- `market_snapshot.parquet`: all historical PIT ticker/date rows
- `equal_weight_top50_benchmark.parquet`: daily benchmark returns and coverage
- `latest_snapshot.csv`: latest PIT universe
- `summary.json`: compact run metadata

The console prints a compact summary and the five strongest/weakest tickers by 5-session relative strength. Generated data remains local and is ignored by Git.
