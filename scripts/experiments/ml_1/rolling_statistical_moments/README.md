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
- Complete trading-session calendar retained in daily IC output; missing IC observations carry reason codes.
- AM (amplitude-modulated) and ES (equal-spacing) HAC estimators compared.
- Bartlett bandwidth sensitivity: 4, 10, 20, and 60 trading sessions.
- Minimum 30 finite daily observations for inferential results.
- Benjamini-Hochberg correction across features separately for each metric, estimator, and bandwidth.
- Predeclared subperiod stability: 2005-2012, 2013-2019, 2020+.
- Within-date pairwise feature correlation diagnostics.
- No portfolio metrics or backtest.

## Run

From repository root:

```powershell
python scripts/experiments/ml_1/rolling_statistical_moments/run_experiment.py
```

## Outputs

Written to:

`data/interim/ml_1/rolling_statistical_moments/`

- `feature_observations.parquet`
- `daily_ic.csv`
- `ic_summary.csv`
- `feature_coverage.csv`
- `feature_redundancy.csv`
- `hac_inference.csv` (AM/ES × IC/Rank IC × bandwidth)
- `ic_missingness.csv` (reason-coded missingness by feature)
- `run_metadata.json`
- `research_report.md`

The adjusted SQLite database is opened read-only. No source data is modified.

## Research Audit 01: HAC status (2026-11-25)

The original first-pass HAC inference is invalid for dates omitted by the minimum cross-section filter: the old implementation drops missing daily IC rows and then treats the remaining observations as equally spaced.

The repository already builds a complete TQBR/EQBR trading-session calendar in `run_experiment.py::load_adjusted_history()`. The current `evaluation.py` does not pass this calendar into the HAC layer. See `llm_memory/research_agent/06_ML_DIRECTION_FEATURE_RESEARCH.md` for the detailed audit log and current next steps.

The HAC implementation now exposes both the Amplitude-Modulated (AM) estimator and an Equal-Spacing (ES) comparator. AM retains actual trading-session lags; ES compresses observed IC dates. The experiment writes a complete calendar-by-feature IC grid, reason-coded missingness diagnostics, and inference sensitivity for bandwidths 4/10/20/60. AM follows the Datta & Du (2012) normalization: calendar-lag score products are divided by the number of observed values S to estimate the long-run variance, then divided by S again for the variance of the observed mean.

The existing IID/AR(1) MCAR simulations are historical validation only. They do not establish robustness to informative missingness, nonstationarity, or regime changes. Normal-reference p-values remain exploratory. No portfolio metrics are calculated.
