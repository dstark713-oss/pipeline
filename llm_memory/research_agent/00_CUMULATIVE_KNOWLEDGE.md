# Cumulative Research Knowledge

Last updated: 2026-11-25

This file is the compact cross-cycle knowledge index for the Research Agent. Detailed project methods and results remain in their canonical project documents; do not duplicate large reports here.

## Stable methodological principles

- The Research Agent develops validated analytical capabilities. It does not make trades, set allocations, or optimize portfolio outcomes.
- Begin with a research question and estimand, not a convenient feature or fashionable model.
- Distinguish data quality, descriptive structure, statistical association, predictive generalization, causal claims, and downstream utility. Evidence for one does not automatically establish another.
- A statistically significant association is not automatically robust, useful, causal, or out-of-sample predictive.
- Preserve temporal availability, point-in-time universe membership, and instrument identity. Explicitly test leakage, lookahead, survivorship/selection bias, missingness, and data provenance.
- Treat dependent observations and finite-sample uncertainty explicitly. Overlapping labels can induce dependence in evaluation observations; do not confuse this with dependence in the input-generating process.
- Feature discovery must be DS-first: statistics, probability, information theory, statistical learning, and time-series analysis. Do not use trader-style indicators or rename them as statistical methods.
- A candidate feature is not accepted solely because it is common, easy to compute, or has high in-sample IC. State its estimand, assumptions, failure modes, and validation plan.
- Do not revisit a closed experiment without an explicit request or concrete new evidence.
- Keep hypotheses, decisions, user-reported observations, code-inspected facts, and runtime-verified results clearly separated.

## Completed research stages

### Primitive research and market-state screener

The first primitive research cycle and screener hypothesis are closed. The screener is a descriptive analytical tool, not a trading-signal or allocation engine. See `03_PRIMITIVE_RESEARCH.md` and `docs/tools/01_primitive_screener.md`.

### ML Direction Prediction: Log Returns

Log returns are the base representation used in the active direction-prediction dataset:
`r_t = ln(P_t / P_{t-1})`.
They are additive over time and scale-normalized, but do not guarantee stationarity. See `06_ML_DIRECTION_FEATURE_RESEARCH.md`.

### ML Direction Prediction: Rolling Statistical Moments

Status: **CLOSED on 2026-11-25**. The completed family comprised rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240-session windows. Closure means the research pass is finished; it does not mean every candidate is approved for the final model. Do not reopen absent explicit user request or concrete new evidence. Exact experiment evidence remains in its dedicated report and project context.

## Active project constraints

The ML Direction Prediction task uses the point-in-time TOP50 cohort, binary adjusted-Close direction from t to t+5, and features available by close t. The agreed WF design is expanding-window with an initial three-year training period, monthly retraining, next-month holdout, and purge of training labels crossing the cutoff.

Portfolio-level metrics are prohibited throughout feature and model research. After approval of the final model, exactly one decisive portfolio-level application run is permitted; it is not a tuning loop. See `01_ROLE_AND_RULES.md` and `06_ML_DIRECTION_FEATURE_RESEARCH.md`.

## Open research questions

Temporal dependence in the return-generating process has been discussed as a possible next DS-first direction, but remains a proposal only. It must first be taught, scoped, distinguished from the closed rolling-moment work, and approved by the user. No implementation is authorized by its presence here.
