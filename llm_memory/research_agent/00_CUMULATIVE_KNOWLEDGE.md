# Cumulative Research Knowledge

Last updated: 2026-11-27

This is the concise, current cross-cycle knowledge base, not a transcript. Replace superseded conclusions instead of accumulating versions.

## Stable methodological principles

- Start from a research question and estimand, not a convenient feature or fashionable model.
- Distinguish descriptive structure, data quality, statistical association, predictive generalization, causal claims, and downstream economic utility.
- A statistically significant association is not automatically robust, useful, causal, or out-of-sample predictive.
- Preserve temporal availability, point-in-time universe membership, and instrument identity. Test leakage, lookahead, survivorship/selection bias, missingness, and provenance.
- Treat dependent observations and finite-sample uncertainty explicitly.
- Feature and hypothesis discovery should be grounded in statistics, probability, information theory, economics, and time-series analysis. Do not disguise trader-style indicators as statistical methods.
- A candidate is not accepted solely because it is common, easy to calculate, statistically significant, or has high in-sample performance.
- Fix test families, horizons, outcomes, controls, and decision criteria before inspecting experiment results.
- Do not revisit closed experiments without explicit request or concrete new evidence.
- Keep user-reported, code-inspected, runtime-verified, and hypothesized claims distinct.

## Completed research

### EDA2 — CLOSED

All seven descriptive EDA2 blocks are complete and interpreted. Consolidated report:
`docs/research/eda2/results/compilation/EDA2_RESULTS_COMPILATION.md`

Key reusable findings:
- Pooled returns are heavy-tailed; individual instruments and historical periods are heterogeneous.
- Signed-return autocorrelation is weak, while absolute and squared returns show stronger temporal dependence.
- Cross-sectional dependence is positive on average but materially heterogeneous across instrument pairs.
- Cross-sectional dispersion is temporally dependent; breadth sign share itself is not similarly persistent.
- Rolling scale varies through time within instruments; cross-period rank stability is partial rather than constant.
- PIT TOP50 ranks move relatively slowly within the universe, while composition changes more often in later periods; membership exit must not be treated as an observed rank.
- Trading activity is highly concentrated, especially by Volume. Value is more economically interpretable for cross-instrument concentration.
- Same-day activity-conditioned return distributions are descriptive only. They do not establish future predictive value.
- PIT universe composition, unequal histories, missing observations, and selection effects must be controlled in subsequent studies.

Do not reopen completed EDA2 blocks without explicit request or concrete material error.

### Log returns

Daily log return (r_t = \ln(P_t/P_{t-1})) is additive over consecutive periods and scale-normalized, but does not guarantee stationarity.

### Rolling Statistical Moments

Closed on 2026-11-25. Do not reopen without explicit request or concrete new evidence.

## STAGE 05 — Hypothesis Research

The user approved exactly two categories of economic hypotheses:

1. **Risk Control:** preserve capital and improve capital-use efficiency through risk-state information, exposure adaptation, and diversification.
2. **Direct Monetization:** identify reproducible effects that can generate additional net return after implementation costs.

Approved initial pool (approved for research, not empirically validated):

Risk Control:
- RC-001 — volatility-state forecasting for exposure adaptation.
- RC-002 — changing asset dependence and systemic portfolio risk.
- RC-003 — unusual activity as a possible warning of future risk.

Direct Monetization:
- DM-001 — relative-return persistence.
- DM-002 — activity and future relative returns.
- DM-003 — heterogeneity and asset-selection opportunity.
- DM-004 — compensation for bearing risk.

Every hypothesis must explain economic mechanism, expected market behavior, exact economic-value mechanism, information advantage and temporal availability, instruments, horizons, data, candidate variables, confounders, applicability, and predeclared confirmation/rejection criteria.

Economic filter:
- No credible Risk Control or Direct Monetization mechanism → do not include in the main registry.
- Risk Control must beat a meaningful baseline and cannot claim success merely by holding more cash.
- Direct Monetization must demonstrate reproducible net value after commissions, slippage, liquidity and turnover.
- Historical profitability, correlation, or statistical significance alone is insufficient.
- EDA-driven and mechanism-driven hypotheses are both allowed. EDA motivates and constrains but does not prove predictive value.

Canonical documents:
- `docs/research/research_hypothesis/`
- `docs/research/hypothesis_research/PLAN.md`
- `docs/research/hypothesis_research/results/`

## Research boundaries

- Stage 05 forms and prioritizes falsifiable economic hypotheses; Stage 06 designs the formal research methodology.
- No experiment begins before its research design is approved.
- No automatic promotion from hypothesis to validated effect or model.
- Preserve PIT membership, missingness, provenance, and temporal validation.
- No live trading, automatic execution, or portfolio allocation decisions are produced by the Research Agent.
- Raw datasets, SQLite, Parquet, caches, and bulky row-level outputs remain outside GitHub.
