# Cumulative Research Knowledge

Last updated: 2026-11-26

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

## Active project: PIT TOP50 EDA

EDA was run locally by the user on 2026-11-25 and its outputs were committed to `docs/research/eda/`. The Research Agent reviewed the report and recorded its interpretation in `docs/research/eda/EDA_ANALYSIS.md`.

Run snapshot:
- 203,403 PIT membership rows, 214 SECIDs, 5,490 panel dates; 5,740 TQBR/EQBR calendar sessions.
- 199,169 bar-available rows (97.918% of membership rows); 4,234 have no board bar.
- 197,955 valid positive adjusted-Close starting observations.
- 1,214 rows flagged bar-available have incomplete OHLC and missing adjusted Close; clarify `bar_available` semantics.
- Panel Close matches the selected adjusted SQLite Close on all 197,955 comparable observations.
- Future endpoint coverage at +1/+5/+20 sessions is 99.682% / 99.406% / 98.574%.
- Pooled return distributions are heavy-tailed; annual return summaries vary materially. These are descriptive results only, with no inference.

The PIT universe is not a constant 50-security cross-section over the entire history: average daily membership was roughly 10-17 in 2005-2009 and reached 50 from 2015 onward. Historical comparisons must account for changing universe size, composition, and coverage.

The arithmetic and logarithmic return means can differ materially under skewed, heavy-tailed distributions. Positive/negative/zero shares are descriptive frequencies, not forecasts. Repeated security-date observations and overlapping horizons are dependent; raw row counts are not independent sample sizes.

Current status: broad EDA is reviewed; targeted diagnostics are proposed and await user approval. No target, label, forecast horizon, feature family, or model is selected. See `05_NEXT_STEPS.md` and `06_ML_DIRECTION_FEATURE_RESEARCH.md`.

No feature engineering, IC, feature-target association, model fitting, walk-forward evaluation, or portfolio metrics are part of the current stage.
