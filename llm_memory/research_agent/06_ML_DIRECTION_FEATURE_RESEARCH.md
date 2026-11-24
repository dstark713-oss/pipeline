

## Research Audit 01: HAC implementation validation update (2026-11-25)

### Repository code inspection

Inspected the current implementation in:
- `scripts/experiments/ml_1/rolling_statistical_moments/evaluation.py`
- `scripts/experiments/ml_1/rolling_statistical_moments/run_experiment.py`
- `scripts/experiments/ml_1/rolling_statistical_moments/config.py`

Confirmed current integration flaw:
- `calculate_daily_ic()` emits rows only when a date-feature pair has at least 20 valid securities, both target classes, and finite Pearson and Spearman correlations.
- `summarize_ic()` groups the emitted rows by feature and calls `newey_west_mean_test()`.
- `newey_west_mean_test()` drops missing values and treats the remaining values as equally spaced.
- Therefore the original inference compresses trading-session time.
- The full market-session calendar is already constructed in `run_experiment.py::load_adjusted_history()` from distinct `tradedate` values across approved boards TQBR/EQBR, sorted and excluding the suspension interval. It is returned by `load_adjusted_history()` and used to reindex each ticker's history, but it is not passed into daily IC inference.
- The natural integration point is to retain the full calendar and pass it to the summary/HAC layer. The daily IC output should also preserve explicit missing date-feature observations (including their cross-sectional N / missingness reason) or otherwise make them reconstructible against the full calendar.

### Calendar-aware HAC implementation and unit tests

A provisional standalone implementation was created locally by the user in `hac_calendar.py`, with tests in `test_hac_calendar.py`.

Latest test result: 6/6 passed:
- IID standard-error sanity check.
- Positive-autocorrelation SE check.
- Missing sessions preserve calendar lags.
- No-missing result matches manual Newey-West calculation.
- Missing-observation count.
- Explicit manual calendar lag-pair verification.

These tests validate basic arithmetic and calendar indexing, not complete statistical validity.

### Monte Carlo results

The user ran four MCAR scenarios (missingness independent of values), with AR(1) generated at phi=0.5.

First run: 500 sessions, 500 simulations, bandwidth 20:
- IID/no missing: coverage 0.944; rejection 0.056.
- IID/20% missing: coverage 0.942; rejection 0.058.
- AR(1)/no missing: coverage 0.932; rejection 0.068.
- AR(1)/20% missing: coverage 0.924; rejection 0.076.

Bandwidth sensitivity at 500 sessions, 2,000 simulations:
- IID coverage deteriorated as bandwidth increased from 10 to 60 (0.952 to 0.914 without missing; 0.954 to 0.922 with 20% missing), consistent with adding noisy unnecessary lag terms in finite samples.
- AR(1) coverage was around 0.932-0.936 at L=10/20 and worse at L=40/60.
- This short-sample experiment showed substantial finite-sample sensitivity.

Bandwidth sensitivity at 5,471 sessions, 1,000 simulations (despite the script's printed footer still incorrectly saying 2,000):
- IID/no missing coverage: L4 0.958, L10 0.958, L20 0.957, L60 0.955.
- IID/20% missing: L4 0.943, L10 0.942, L20 0.942, L60 0.943.
- AR(1)/no missing: L4 0.914, L10 0.945, L20 0.951, L60 0.951.
- AR(1)/20% missing: L4 0.922, L10 0.942, L20 0.949, L60 0.951.

Interpretation:
- Longer series reduce the finite-sample instability of larger bandwidths.
- For this specific stationary AR(1), L20/L60 achieved coverage close to nominal 95%; L4 under-covered.
- For IID, increasing bandwidth did not help and slightly reduced coverage.
- This does not select a production bandwidth. The real IC process may have more complex dependence, regime shifts, and informative missingness.
- Correct the Monte Carlo script's printed simulation-count footer to 1,000 for the long-series run if retained.

### Important methodological literature to consider

Datta & Du (2012), Federal Reserve IFDP 1060, *Nonparametric HAC Estimation for Time Series Data with Missing Observations*:
https://www.federalreserve.gov/econres/ifdp/nonparametric-hac-estimation-for-time-series-data-with-missing-observations.htm

The paper formalizes two HAC approaches for missing observations:
- Amplitude Modulated (AM): preserve the original time index and treat missing observations as non-serially correlated.
- Equal Spacing (ES): relabel observed values as equally spaced and apply HAC in observation time.
It warns that simply estimating the underlying process spectrum using only observed data can produce incorrect inference. The paper finds ES preferable in many settings due to lower bias, while AM may be preferable for small samples and low autocorrelation.

The current calendar-aligned zero-score implementation is closest in spirit to an AM estimator. Before treating it as final, compare its exact normalization and finite-sample behavior against the formal AM construction and run a fair AM-vs-ES simulation comparison. Calendar preservation is not automatically the only theoretically defensible missing-data HAC approach.

### Next steps

1. Validate the exact AM estimator formula/normalization against Datta & Du (2012), rather than relying only on the current custom derivation and MCAR simulation.
2. Implement a comparator Equal Spacing HAC estimator for diagnostic comparison; do not silently substitute it for calendar-time inference.
3. Expand simulations beyond MCAR: test missingness dependent on observed process values / cross-sectional N and assess bias/coverage. Clearly distinguish missingness mechanisms.
4. Integrate inference into the existing pipeline using the already available complete TQBR/EQBR session calendar.
5. Run bandwidth sensitivity L=4, 10, 20, 60 on actual daily IC and Rank IC, retaining missing dates and missingness diagnostics.
6. Add temporal block-bootstrap uncertainty, then diagnose skewness coverage and IC temporal stability.
7. No portfolio metrics and no feature-family transition until Audit 01 is complete.

Current status: unit tests pass; calendar-aware HAC is provisionally tested under IID/AR(1) with MCAR, but the exact missing-data estimator and real-data inference remain unvalidated.
