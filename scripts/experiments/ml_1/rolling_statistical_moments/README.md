# Rolling Statistical Moments

Folder: `scripts/experiments/ml_1/rolling_statistical_moments/`

## Purpose

First-pass research on rolling mean, variance, skewness, and Fisher excess kurtosis calculated from daily adjusted-close log returns.

## Predeclared feature grid

- Windows: 20, 60, 120, 240 trading sessions.
- Families: mean, variance, skewness, excess kurtosis.
- Total: 16 features.
- Full windows only (`min_periods = window`).
- Variance uses `ddof=1`.
- Skewness and kurtosis use pandas bias-corrected rolling estimators.
- Kurtosis is Fisher excess kurtosis (normal distribution = 0).

## Target and universe

- Signal-date universe: PIT TOP50 members on date t with `bar_available=1`.
- Features use adjusted daily history for the corresponding SECID.
- Target: 1 if adjusted Close at t+5 is above adjusted Close at t; 0 if below.
- Ties and unavailable target endpoints are excluded.
- Features are calculated through close t; no future data enters a feature.
- No forward-fill; missing sessions are not bridged.

## Evaluation

- Daily cross-sectional Pearson IC (point-biserial with binary target).
- Daily cross-sectional Spearman Rank IC.
- Minimum 20 valid securities per date.
- Newey-West/HAC maximum lag 4.
- Benjamini-Hochberg correction separately for IC and Rank IC.
- Predeclared subperiod stability: 2005-2012, 2013-2019, 2020+.
- Within-date pairwise feature correlation diagnostics.
- No portfolio metrics or backtest.

## Run

From repository root:

```powershell
python scripts/experiments/ml_1/rolling_statistical_moments/run_experiment.py
```

Dependencies expected from the existing project environment: `numpy`, `pandas`, and a Parquet engine such as `pyarrow`.

## Outputs

Written to:

`data/interim/ml_1/rolling_statistical_moments/`

- `feature_observations.parquet`
- `daily_ic.csv`
- `ic_summary.csv`
- `feature_coverage.csv`
- `feature_redundancy.csv`
- `run_metadata.json`
- `research_report.md`

The adjusted SQLite database is opened read-only. No source data is modified.
