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

## Research Audit 01: HAC status (2026-11-25)

The original first-pass HAC inference is invalid for dates omitted by the minimum cross-section filter: the old implementation drops missing daily IC rows and then treats the remaining observations as equally spaced.

The repository already builds a complete TQBR/EQBR trading-session calendar in `run_experiment.py::load_adjusted_history()`. The current `evaluation.py` does not pass this calendar into the HAC layer. See `llm_memory/research_agent/06_ML_DIRECTION_FEATURE_RESEARCH.md` for the detailed audit log and current next steps.

A provisional calendar-aware HAC implementation has passed six local unit tests and Monte-Carlo checks for IID and stationary AR(1) processes with MCAR missingness. This is not yet production validation. In particular, formal missing-data HAC literature distinguishes Amplitude Modulated and Equal Spacing estimators; compare both and validate the exact formula before using real-data p-values.

No updated IC inference or portfolio metrics have been generated as part of this audit.
