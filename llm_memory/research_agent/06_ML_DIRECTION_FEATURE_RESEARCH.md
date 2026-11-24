# ML Direction Prediction: Feature Research Context

Last updated: 2026-11-24

## Purpose

This document records the agreed research context for the ML Direction Prediction feature-research track. It is separate from the earlier instrument-level primitive/screener research. Financial OHLCV data is the experimental domain for developing general applied-DS, statistical-learning, and time-series-analysis skills. The objective is to understand what information different feature families extract, not to collect trading indicators.

## Research workflow

For each feature family:
1. Explain the method, intuition, mathematics, and interpretation.
2. Form explicit hypotheses and agree on experiment parameters before running tests.
3. Implement a reproducible experiment.
4. Evaluate information content, coverage, temporal stability, and redundancy.
5. Record findings and limitations. Do not promote a feature into the model automatically.
6. Study feature interactions/conditional information later; individual IC is not a complete feature-selection criterion.

Do not jump prematurely to model construction, portfolio optimization, or broad feature catalogs. Teach the underlying methods as part of the process.

## Model task and evaluation firewall

- Dataset: daily OHLCV panel built from historical point-in-time TOP50 Russian equities.
- Signal-date universe: PIT TOP50 membership on date t; never use future membership to define the signal-date cohort.
- Prediction horizon: 5 trading sessions.
- Target: binary direction from adjusted Close at t to adjusted Close at t+5:
  - 1 when adjusted_close[t+5] > adjusted_close[t]
  - 0 when adjusted_close[t+5] < adjusted_close[t]
  - equal prices and unavailable endpoints are excluded from target evaluation.
- Features must use only information available by the close of t.
- The established final model WF protocol remains: expanding window, initial 3 years of training, monthly retraining, each next month held out, and purge training observations whose 5-session target extends beyond the training cutoff.
- During feature/model development, use statistical and model diagnostics only. Do not inspect or optimize portfolio metrics.
- After approval of the final model, there is one decisive portfolio run. Portfolio metrics must not be used for iterative feature/model selection or tuning.
- Research Agent does not make trading decisions or optimize trading strategies.

## Feature Research 01: Log Returns

Daily log return:
r_t = ln(P_t / P_{t-1}).

Log returns are additive across consecutive periods and provide a scale-normalized representation of price changes. They are a base representation, not by themselves a proven predictor. Log returns do not guarantee stationarity.

## Feature Research 02: Rolling Statistical Moments

### User-agreed candidate grid

Four statistics across four rolling windows, 16 candidate features total:

- Rolling mean: 20, 60, 120, 240 sessions.
- Rolling variance: 20, 60, 120, 240 sessions.
- Rolling skewness: 20, 60, 120, 240 sessions.
- Rolling Fisher excess kurtosis: 20, 60, 120, 240 sessions.

The user explicitly prefers extending the skewness/kurtosis windows to 120 and 240 because 60 sessions may still be noisy. All four statistics use the same window grid for a comparable first experiment.

Mean is retained as an exploratory/control feature to inspect its behavior, not because it is assumed to be predictive. Variance is included without annualization: the experiment measures variance of daily log returns.

### Definitions

- Input series: daily log returns from adjusted Close.
- Mean: rolling arithmetic mean.
- Variance: sample variance, ddof=1.
- Skewness: bias-corrected sample skewness.
- Kurtosis: bias-corrected Fisher excess kurtosis (normal distribution = 0).
- Rolling windows: 20, 60, 120, 240 market sessions.
- min_periods equals the full window length.
- No forward-fill or synthetic imputation.
- A return is computed only between adjacent market sessions with valid adjusted closes. Missing closes remain missing; do not bridge a missing session by calculating a multi-session return and treating it as a one-session return.
- A feature at t may use the close at t, because the signal is formed after that close. No observations after t may enter its calculation.

### Hypotheses

- Mean may represent local drift, but its predictive information is uncertain and it may be dominated by a small number of large returns.
- Variance may describe local dispersion/volatility state.
- Skewness may capture asymmetry in recent returns, including downside/upside tail imbalance.
- Excess kurtosis may capture tail extremity/heavy-tailed behavior, but its finite-window estimate can be unstable.
- Larger windows can stabilize higher-moment estimates but may mix different market regimes and react more slowly. A larger window is not automatically better.

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

As of 2026-11-24, the Rolling Statistical Moments experiment has been implemented and executed locally by the user. Its initial report exists, but the inferential results are preliminary because the HAC time index was compressed when dates with fewer than 20 valid securities were dropped. See the audit section below. Do not describe the initial p-values as validated.


## Rolling Statistical Moments: first execution results and audit state

### Execution snapshot (2026-11-23/24)

The user ran the experiment locally. Reported dataset:
- 195,601 signal rows.
- 5,471 signal dates.
- 188 distinct securities across the historical panel.
- 16 features (four statistics x four windows).
- Target and universe as specified above.

Initial descriptive findings (not final inferential conclusions):
- Rolling variance had negative mean IC and Rank IC at all four windows. Mean IC became more negative with longer windows; variance-240 had mean IC about -0.0416 and mean Rank IC about -0.0241.
- Rolling mean had positive IC/Rank IC, increasing with window length; mean-240 had mean IC about +0.0249 and Rank IC about +0.0316.
- Fisher excess kurtosis had modest negative IC/Rank IC across windows; approximate mean IC range -0.011 to -0.021.
- Skewness had weak/near-zero standalone IC, especially at 20/60/120; 240 showed a somewhat more negative Pearson IC, while Rank IC remained weak.
- Long-window features showed substantial within-date redundancy. Examples of median pairwise correlations: variance-60 vs variance-120 about 0.917; variance-120 vs variance-240 about 0.907; mean-120 vs mean-240 about 0.769.
- Coverage declined with window length. Mean/variance coverage: 20=97.5%, 60=94.8%, 120=89.1%, 240=78.4%. Skewness coverage was unexpectedly lower: 20=89.3%, 60=90.0%, 120=84.8%, 240=76.0%. This requires a code/data diagnostic; do not assume the missingness is benign.

### Critical inference flaw

The initial implementation calculated daily cross-sectional IC, dropped dates with fewer than 20 valid securities, then ran Newey-West/HAC with max_lags=4 on the remaining rows. This compresses time: two adjacent rows in the filtered series may be separated by multiple actual trading sessions, while HAC treats them as one lag apart. Therefore the reported HAC standard errors, p-values, and BH-adjusted q-values are not reliable as currently computed.

The initial HAC bandwidth of 4 also needs sensitivity analysis because five-session labels overlap and feature/market-state dependence may persist longer. Values displayed as 0.00000 are rounded, not literal zero.

### Research Audit 01: next required work

Do not move to a new feature family or model construction until this audit is completed.

1. Recompute inference using the full trading-session calendar, preserving missing IC dates as missing rather than compressing time. Ensure HAC covariance uses actual session lags.
2. Run bandwidth sensitivity at 4, 10, 20, and 60 trading sessions, with assumptions documented.
3. Add a temporal block-bootstrap uncertainty estimate as a complementary check.
4. Diagnose the skewness coverage gap versus mean/variance for identical windows. Inspect estimator output, zero/near-zero variance, missing return patterns, and implementation details.
5. Inspect daily IC distributions and temporal stability, including subperiod coverage and the long-window sample-size limitations.
6. Reassess the apparent variance/mean/kurtosis patterns only after corrected inference. Preserve the descriptive findings as provisional.
7. Keep portfolio metrics out of this audit and out of all iterative feature/model selection.

### Interpretation constraints

- Negative variance IC is an association with a lower probability of an up label, not evidence that volatility causes losses.
- Positive rolling-mean IC may reflect drift/momentum, but is not yet evidence of robust predictive value.
- Weak standalone skewness IC does not prove absence of conditional or interaction information.
- Correlation is a redundancy diagnostic, not proof that features are interchangeable.
- Do not select or discard features solely from the first-pass IC ranking.

Current working point: Research Audit 01 for Rolling Statistical Moments, not the next feature family.
