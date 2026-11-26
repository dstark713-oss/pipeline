# Stage 05 — Hypothesis Research Plan

Last updated: 2026-11-27  
Status: approved plan; no experiments started

## 1. Purpose
Build and maintain a falsifiable research program for two kinds of economic value:
1. **Risk Control:** preserve capital and improve the efficiency of capital use.
2. **Direct Monetization:** identify reproducible sources of additional net return.

Stage 05 forms and prioritizes hypotheses. Formal experiment methodology belongs to Stage 06 — Research Design & Method Selection. Approval of this plan does not authorize implementation of experiments.

## 2. Inputs
- EDA2 consolidated results: `../eda2/results/compilation/EDA2_RESULTS_COMPILATION.md`.
- Seven approved hypothesis passports: `../research_hypothesis/`.
- Current PIT TOP50 dataset contract and source documentation.
- External economic/academic literature where useful, with source and publication-date provenance.

EDA2 is descriptive. It may motivate a hypothesis, identify confounders, and constrain data design, but it does not establish predictive effects.

## 3. Approved hypothesis pool

Risk Control:
- RC-001 — volatility-state forecasting for exposure adaptation.
- RC-002 — changing asset dependence and systemic portfolio risk.
- RC-003 — unusual trading activity as a possible risk warning.

Direct Monetization:
- DM-001 — relative-return persistence.
- DM-002 — trading activity and future relative returns.
- DM-003 — heterogeneity and asset-selection opportunity.
- DM-004 — compensation for bearing risk.

## 4. Research workflow

### A. Select one hypothesis
Use `../research_hypothesis/RESEARCH_PRIORITY.md` as the starting order. Any departure must be justified. Do not start several loosely specified experiments at once.

### B. Refine the economic thesis
State the mechanism and competing explanations; distinguish predicted market behavior from economic value; specify why information may be available before the effect; define assets, universe and decision timestamp; register expected sign or competing alternatives.

### C. Formalize the research question before code
Define estimand and outcome; formation and evaluation horizons; PIT eligibility and exit/entry handling; missing-data rules; candidate variables and timestamps; confounders and controls; baselines; statistical tests and uncertainty; multiplicity families; temporal validation; robustness; confirmation, rejection and inconclusive outcomes.

### D. Economic implementation gate
For **Risk Control**, define the risk outcome and decision use; compare with a meaningful baseline at comparable exposure/return or account for reduced exposure and opportunity cost; include cash yield assumptions, turnover, commissions, slippage, liquidity and tail behavior where relevant.

For **Direct Monetization**, define the source of incremental expected return; evaluate relative-return prediction separately from portfolio implementation; define realistic costs, slippage, liquidity, capacity, turnover and benchmark; require positive net economic value, not only statistical significance or gross historical returns.

### E. Approval and execution
1. Publish a hypothesis-specific research design under Stage 06 documentation.
2. Obtain explicit user approval.
3. Implement only the approved scope.
4. Preserve reproducibility, PIT integrity, provenance, and code/data versions.
5. Report actual execution provenance. GitHub inspection is not local runtime execution.

### F. Evidence review and registry update
Classify results as supported within a stated scope, rejected under predeclared criteria, or inconclusive. Update passport, registry and priority only after reviewing evidence. Preserve failed hypotheses and reasons; do not silently rewrite them.

## 5. Scientific safeguards
- No random shuffling of time-dependent observations.
- Prevent lookahead, leakage, survivorship and PIT selection bias.
- Handle overlapping outcomes and dependent observations with appropriate inference.
- Declare multiple-testing families and apply correction where appropriate.
- Report effect sizes, uncertainty, coverage, and stability, not p-values alone.
- Separate descriptive, inferential, predictive, causal, and economic claims.
- Both EDA-driven and mechanism-driven hypotheses are allowed.
- No hypothesis is accepted solely because it has high historical profitability.
- Post-hoc window, threshold, universe, or metric selection must be labeled exploratory and independently validated.

## 6. Initial research sequence
1. DM-001 — relative-return persistence.
2. RC-001 — volatility-state forecasting.
3. DM-002 — activity and future relative returns.
4. DM-004 — compensation for bearing risk.
5. RC-002 — systemic dependence.
6. DM-003 — heterogeneity and selection opportunity.
7. RC-003 — activity as a risk warning.

This is a research-priority order, not a claim about profitability.

## 7. Out of scope
Trading strategies, BUY/SELL recommendations, portfolio allocation, live execution, assuming hypotheses are true, implementing models before Stage 06 design approval, treating minute OHLCV as complete order-flow data, or reopening closed EDA2 blocks without material reason.

## 8. Expected outputs
Versioned hypothesis passports; central registry; research-priority record; approved Stage 06 research designs; compact experiment reports under `results/`; updated evidence status and limitations.
