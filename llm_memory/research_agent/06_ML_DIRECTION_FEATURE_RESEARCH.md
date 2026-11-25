# ML Research: EDA and Prediction-Problem Design

Last updated: 2026-11-25

## Project objective

Use the PIT TOP50 MOEX daily market dataset to investigate whether the observed data supports a useful prediction problem. The final output is not assumed to be one model. The research may produce multiple tasks/models, a different analytical capability, or a conclusion that prediction is not justified.

Methodology is DS-first: statistics, probability, information theory, time-series analysis, statistical learning, uncertainty, heterogeneity, and nonstationarity. Do not use trader-style indicators or price-action heuristics as feature templates. Explicit exclusions include ATR, RSI, MACD, Bollinger Bands, stochastic oscillators, and candlestick patterns. OHLCV is the raw observation domain, not a mandate to construct trading signals.

## Current stage: descriptive EDA

Status: **approved; code committed to GitHub; user execution pending**.

Canonical specification: `docs/research/eda/EDA_SPEC.md`.

Implementation: `scripts/experiments/ml_1/eda/`.

The EDA describes:
- temporal panel coverage and PIT membership dynamics;
- distributions of adjusted OHLC, volume, value, value_60d, rank, and universe_size;
- annual and instrument-level heterogeneity;
- internal OHLC, price, volume/value, and bar-availability consistency;
- adjusted Close[t] to Close[t+1], Close[t+5], and Close[t+20] empirical behavior.

The three horizons are descriptive comparisons only. They do not define a target, label, model, or chosen forecast horizon. `numtrades` is absent from the current EDA data contract and is excluded.

No repeated general structure/quality audit. No feature engineering, IC, feature-target association, model fitting, walk-forward evaluation, or portfolio metrics during this EDA stage. No forward-fill, synthetic bars, outlier removal, or source-data mutation.

The user will pull the implementation, run it against local Parquet/SQLite data, and push the compact outputs to `docs/research/eda/`. Until then, code is committed but runtime results are not verified.

## Completed prior research

### Log returns

Daily log return representation:
`r_t = ln(P_t / P_{t-1})`.
It is additive over consecutive periods and scale-normalized, but does not guarantee stationarity. This is a statistical representation, not a proven predictor.

### Rolling Statistical Moments

Status: **CLOSED on 2026-11-25**. The completed experiment covered rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240-session windows. Do not reopen, repeat IC/correlation analysis, or propose additional diagnostics absent explicit user request or concrete new evidence. Closure does not imply automatic promotion of candidates into any future model.

## After EDA

Only after inspecting the actual EDA evidence, formulate the prediction problem from the data:
- decide whether prediction is justified at all;
- identify which outcome variables and horizons merit further study;
- determine whether the research needs one task/model, multiple tasks/models, or no model;
- define labels, sample eligibility, timestamp, baselines, leakage controls, validation and evaluation only after the empirical questions are clear.

Do not assume a binary up/down label, fixed 5-session horizon, fixed model family, or predeclared walk-forward protocol at this stage. No model implementation until the user approves a separate model-design plan.

## Research boundaries

<<<<<<< HEAD
### First-pass evaluation design

- Signal-date cohort: PIT TOP50 members on t with an actual current bar.
- Lookback/features: use adjusted daily history for the corresponding SECID, without expanding the signal-date universe.
- Target: binary adjusted-Close direction from t to t+5, as defined above. This is the ML Direction Prediction target and must not be replaced by the older primitive-research execution proxy (Close[t+H] / Open[t+1] - 1).
- Cross-sectional Pearson IC per date. With a binary target this is a point-biserial correlation.
- Cross-sectional Spearman Rank IC per date; interpret with awareness of ties in the binary target.
- Minimum valid cross-section: 20 securities per date.
- Report daily N, mean/median IC, IC standard deviation, positive-IC share, and predeclared subperiod stability (2005-2012, 2013-2019, 2020+).
- Use Newey-West/HAC with maximum lag 4 as a first correction for serial dependence induced by overlapping 5-session labels. This is a diagnostic, not a guarantee of valid inference.
- Apply Benjamini-Hochberg correction separately to Pearson IC and Rank IC test families across the 16 predeclared features.
- Include feature coverage and redundancy diagnostics; do not select features by maximum IC alone.
- No portfolio metrics, strategy backtests, or portfolio optimization in this experiment.

### Interpretation guardrails

- Positive IC means larger feature values are associated with a higher probability of an up label; negative IC means the reverse.
- A statistically significant IC does not establish economic usefulness, causality, or out-of-sample robustness.
- A feature with weak standalone IC may contain conditional or interaction information.
- Correlated features are not automatically redundant in all nonlinear/conditional senses; correlation is a diagnostic, not a sole exclusion rule.
- Do not silently change windows, formulas, universe, target, or evaluation parameters after viewing results. Any changes must be recorded as a new experiment/specification revision.

## Implementation status

Feature Research 01 (Log Returns) is the base return representation. Feature Research 02 (Rolling Statistical Moments) has been executed, audited, and explicitly closed by the user on 2026-11-25. Its final experiment report and audit artifacts are the record of that stage.

Do not reopen the 16 rolling-moment features (mean, variance, skewness, Fisher excess kurtosis over 20/60/120/240 sessions), repeat their IC/correlation/conditional-information discussion, or propose further diagnostics on them unless the user explicitly reopens the stage or new evidence identifies a concrete defect. The earlier audit plan below is historical and superseded by the closure record; it is not an active task list.

## Research Audit 01: closure record (2026-11-25)

- Status: **CLOSED**.
- The experiment used 195,601 signal rows, 5,471 dates, 188 securities, and 16 features.
- Calendar-aware inference integration and the experiment report were completed in the repository workflow. The detailed report is the evidence source for exact methodology and results.
- The user explicitly instructed: stop revisiting these features and move to the next feature family.
- Do not infer that the features are approved for the final model. Stage closure means the research pass is complete, not that all candidates are selected or promoted.
- No portfolio metrics are permitted during ongoing feature/model research.

## DS-first feature research constraint and next direction

The user explicitly prohibits trader-style technical indicators/features as the basis for the new ML predictor. ATR is a named example of a trader-style feature that must not become a template. Do not propose RSI, MACD, Bollinger Bands, stochastic oscillators, candle patterns, or trader-style price-action heuristics. Do not relabel such indicators as statistical features. The OHLCV dataset is a raw observation domain, not an instruction to create candlestick signals.

Feature discovery must be grounded in data science, statistics, statistical learning, probability, information theory, and time-series analysis. Start from a research question about the data-generating process and define what is being measured, why the measurement is statistically meaningful, what assumptions it needs, and how it can fail. The legacy ATR-based tool may remain separate and operational, but it is not a methodological precedent for this ML project.

The prior discussion identified **Statistical Learning under Uncertainty** as a broader methodological direction: study weak signals, dependence between observations, estimation uncertainty, and unstable/nonstationary distributions. This is a methodological research direction, not an approved feature family.

### Candidate next research question (proposal only): temporal dependence

Investigate whether the return-generating process contains reproducible serial-dependence structure at selected lags, and whether a compact, statistically defensible representation adds information about the fixed t-to-t+5 direction target.

Potential concepts to teach before specification:
- Autocovariance and autocorrelation: what they measure and what they do not.
- Partial autocorrelation / conditional dependence after accounting for intermediate lags.
- Sampling uncertainty of dependence estimates in finite, noisy samples.
- Multiple testing and lag-selection bias.
- Nonstationarity, regime instability, and cross-sectional heterogeneity.
- Dependence induced by overlapping five-session labels versus dependence in the input process itself.

This must not become a bulk ACF/PACF indicator catalog. First establish whether the question is distinct from the completed rolling-moment family, define the statistical estimand, choose a small predeclared lag design, and specify inference/validation. No implementation until the user approves the design.

The previously suggested OHLC gap/intraday/range/CLV/wick decomposition is **withdrawn** because it drifts toward trader-style price-action feature engineering and was not aligned with the user's DS-first constraint.

## Active next action

Explain the DS-first research direction and the temporal-dependence question, including its mathematical foundations and relationship to the already completed rolling-moment experiment. Then propose a narrow experiment specification for user review. Do not write code or run an experiment until approved.
## Active next action

<<<<<<< HEAD
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


## HAC integration implementation (2026-11-25)

Implementation is staged on branch `hac-audit-integration`; it has not yet been run against the local dataset or merged into `main`.

### Code changes

- `hac_calendar.py` now exposes two estimators:
  - AM: calendar-aligned amplitude-modulated scores, with Bartlett lag pairs measured in trading sessions and Datta & Du normalization by observed count S.
  - ES: equal-spacing comparator, where finite observations are compressed and lags refer to observed-IC time.
- Both return the observed mean, long-run variance estimate, variance of the mean, standard error, normal-reference t statistic/p-value, observation count, calendar-session count, and bandwidth.
- Non-finite IC values are treated as missing; invalid bandwidth types, duplicate dates, duplicate calendar sessions, and dates outside the calendar are rejected.
- `evaluation.py` now creates a complete calendar-session × feature IC grid, preserves missing IC values with reason codes, computes descriptive IC summaries separately, and generates AM/ES inference for Pearson IC and Rank IC at bandwidths 4/10/20/60.
- BH correction is applied across features separately for each metric × estimator × bandwidth specification.
- `run_experiment.py` passes the signal-period slice of the existing TQBR/EQBR calendar and writes `hac_inference.csv` and `ic_missingness.csv`.
- The report and README now describe the estimator distinction and limitations. Portfolio metrics remain disabled.

### Added tests

The existing manual-formula and calendar-lag tests remain. Additional tests cover AM/ES equivalence without missing observations, expected divergence with calendar gaps, non-finite values treated as missing, and bandwidth type validation.

### Validation status

These changes are not yet runtime-validated. The previous unit tests and MCAR simulations validate the earlier AM implementation, not every new integration change. Before merge:
1. Run the complete test suite for this experiment.
2. Run the experiment on the actual dataset.
3. Inspect row counts, missingness reason counts, AM/ES outputs, and bandwidth sensitivity.
4. Confirm that the generated full-calendar grid covers exactly the panel signal period.
5. Review AM/ES differences as a sensitivity diagnostic; do not select the smaller p-value.
6. Keep all portfolio metrics and strategy evaluation out of this audit.

No new Monte Carlo run is currently planned. Add simulations only if runtime validation exposes a specific unresolved estimator property.
=======
Teach and agree the OHLC decomposition family specification before coding. The next discussion should cover intuition, exact formulas, edge cases, mathematical relationships, hypotheses, and predeclared tests. Do not start model fitting or portfolio evaluation.
>>>>>>> 6ea9da5ed8cb22bb5a3d28ea492f4a2e9db86e7e
=======
- Research Agent produces validated analytical capabilities; it does not make trading/allocation decisions.
- No trader-style feature engineering or disguised technical indicators.
- No feature/model implementation without an approved research plan.
- Do not revisit closed work without explicit request or concrete new evidence.
- Keep PIT membership, SECID identity, market-session timing, and missingness intact.
- Never forward-fill missing prices or bridge missing sessions.
- Do not automatically delete extreme observations.
- Portfolio metrics are outside this EDA and prediction-design work. Any later change to evaluation scope requires explicit agreement.
- GitHub inspection is not execution. Runtime claims require actual user-supplied or authorized execution evidence.
>>>>>>> 09bf043237e486da8f2d056114990f4bb7abad66
