# ML Direction Prediction: Feature Research Context

Last updated: 2026-11-25 (stage closure update)

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

## Current status and next action

Rolling Statistical Moments is closed. The OHLC decomposition proposal is withdrawn. Temporal dependence remains a possible DS-first research direction, not an approved feature family or experiment. No next feature family is approved yet.

Follow `RESEARCH_WORKFLOW.md`: first propose a research plan, explain the statistical question and its distinction from completed work, and obtain user approval. Do not write code or run an experiment before approval.
