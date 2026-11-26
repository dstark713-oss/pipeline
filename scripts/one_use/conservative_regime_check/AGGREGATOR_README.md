# Daily regime metrics aggregator

Aggregates the 4k-5k row `daily_regime_metrics.csv` into compact human-readable outputs.

## Run

From repository root:

```powershell
python scripts/one_use/conservative_regime_check/aggregate_regime_metrics.py
```

Optional:

```powershell
python scripts/one_use/conservative_regime_check/aggregate_regime_metrics.py --windows 20,60,120,250 --breadth-thresholds 0.4,0.5,0.6
```

Default input:
`data/interim/one_use/regime_check/daily_regime_metrics.csv`

Default output:
`data/interim/one_use/regime_check/aggregated/`

## Outputs

- `AGGREGATE_REPORT.md`: short narrative summary.
- `period_aggregates.csv`: full sample, calendar years, quarters, trailing windows.
- `latest_vs_history.csv`: latest daily values and trailing 20/60/120 means vs full-history mean.
- `breadth_episodes.csv`: time above selected breadth thresholds, episode lengths and current streak.
- `monthly_aggregates.csv`: monthly summaries.
- `aggregate_metadata.json`: input range and run configuration.

This is descriptive aggregation only. It does not run inferential tests, attribute causes, evaluate fundamentals, or generate an investment signal.
