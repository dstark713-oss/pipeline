# Aggressive Hypothesis Confirmation

Runs the first historical confirmation pass for the five market hypotheses. It does not perform the separate falsification stage and does not produce BUY/SELL decisions or position sizes.

## Run

From the repository root:

```powershell
git pull
python scripts/one_use/aggressive_hypothesis_confirmation/run_hypothesis_confirmation.py
```

## Inputs

- data/interim/aggressive_market_snapshot/market_snapshot.parquet
- data/interim/aggressive_market_snapshot/equal_weight_top50_benchmark.parquet
- data/processed/moex_daily_adjusted.sqlite, table adjusted_daily_bars

The module imports the existing market-snapshot builder for adjusted-board aggregation policy and reads the database in read-only mode. Future ticker returns use adjusted closes over the global adjusted-bar calendar. Future benchmark returns compound realized daily equal-weight PIT TOP50 returns.

## Outputs

One Markdown report is generated at docs/aggressive_hypothesis_confirmation_report.md.

All machine-readable outputs are local under data/interim/aggressive_hypothesis_confirmation/:
- hypothesis_summary.csv
- period_stability.csv
- daily_group_differences.csv
- impulse_path_metrics.csv
- h4_volatility_diagnostics.csv
- h4_volatility_daily.csv

## Fixed signal definitions

All thresholds are calculated cross-sectionally by date:
- H1: positive 5-session return in the top quintile.
- H2: positive 20-session relative strength in the top quintile.
- H3: positive absolute returns over both 5 and 20 sessions.
- H4: positive 5-session relative strength in the top quintile; inspect its association with 20-session realized volatility and compare low-volatility versus high-volatility members within that high-RS group.
- H5: negative 5-session and 20-session relative strength, both in the bottom quintile.

The primary outcome is forward relative return versus equal-weight TOP50 over 3, 5, 10, and 20 sessions. Signal groups are compared with the same-date complement, except the H4 subgroup contrast, which compares low-volatility high-RS names with high-volatility high-RS names.

Statistical inference uses Newey-West standard errors on daily spreads, with lag equal to horizon minus one. Circular block-bootstrap confidence intervals use a block length equal to the forward horizon. Benjamini-Hochberg q-values adjust the pooled set of reported hypothesis/horizon tests; p-values are normal approximations to Newey-West t-statistics and should be treated as screening diagnostics.

The report is confirmation-stage evidence only. A separate falsification module is required before any trading decision.
