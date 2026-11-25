# Cumulative Research Knowledge

Last updated: 2026-11-25

This is the concise, current cross-cycle knowledge base, not a transcript. Replace superseded conclusions instead of accumulating versions.

## Stable methodological principles

- Start from a research question and estimand, not a convenient feature or fashionable model.
- Distinguish descriptive structure, data quality, statistical association, predictive generalization, causal claims, and downstream utility.
- A statistically significant association is not automatically robust, useful, causal, or out-of-sample predictive.
- Preserve temporal availability, point-in-time universe membership, and instrument identity. Test leakage, lookahead, survivorship/selection bias, missingness, and provenance.
- Treat dependent observations and finite-sample uncertainty explicitly.
- Feature discovery is DS-first: statistics, probability, information theory, statistical learning, and time-series analysis. Do not use trader-style indicators or rename them as statistical methods.
- A candidate is not accepted solely because it is common, easy to calculate, or has high in-sample IC.
- Do not revisit closed experiments without explicit request or concrete new evidence.
- Keep user-reported, code-inspected, runtime-verified, and hypothesized claims distinct.

## Completed research

### Primitive research and market-state screener

Closed. The screener is a descriptive analytical tool, not a trading-signal or allocation engine. See `03_PRIMITIVE_RESEARCH.md` and `docs/tools/01_primitive_screener.md`.

### Log returns

Daily log return `r_t = ln(P_t / P_{t-1})` is additive over consecutive periods and scale-normalized, but does not guarantee stationarity.

### Rolling Statistical Moments

**CLOSED on 2026-11-25.** The experiment covered rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240 sessions. Closure means the research pass is finished, not that every candidate is approved for future use. Do not reopen without explicit request or concrete new evidence.

## Active project state

The active project is exploratory research on the PIT TOP50 daily market dataset. The current stage is descriptive EDA, approved and implemented in `scripts/experiments/ml_1/eda/`; local execution and evidence are pending.

The EDA compares adjusted Close[t] with Close[t+1], Close[t+5], and Close[t+20] as descriptive empirical outcomes. These horizons do not define a selected prediction target. The project does not assume one model, a binary label, or even that a predictive model is warranted.

No feature engineering, IC, feature-target association, model fitting, walk-forward evaluation, or portfolio metrics are part of the current EDA stage. See `06_ML_DIRECTION_FEATURE_RESEARCH.md` and `docs/research/eda/EDA_SPEC.md`.
