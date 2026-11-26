# Next Steps and Open Research

Last updated: 2026-11-27

## Current stage: STAGE 05 — Hypothesis Research

**Status:** architecture and initial hypothesis pool approved; research plan documented; no hypothesis experiments implemented or run.

Stage 05 has exactly two categories:
- **Risk Control:** preserve capital and improve capital-use efficiency.
- **Direct Monetization:** identify reproducible sources of additional net return.

Approved initial pool:
- RC-001 — volatility-state forecasting for exposure adaptation.
- RC-002 — changing asset dependence and systemic portfolio risk.
- RC-003 — unusual trading activity as a possible risk warning.
- DM-001 — relative-return persistence.
- DM-002 — trading activity and future relative returns.
- DM-003 — heterogeneity and asset-selection opportunity.
- DM-004 — compensation for bearing risk.

Canonical documents:
- Hypothesis passports: `docs/research/research_hypothesis/`
- Stage plan and experiment results: `docs/research/hypothesis_research/`
- Stage 05 specification: `docs/architecture/MASTER_SPECIFICATION.md`

## Research sequence

1. Refine the economic mechanism and falsifiable statement for the selected hypothesis.
2. Define its estimand, target/outcome, timestamp, horizon, PIT universe, and data availability.
3. Identify confounders and competing explanations.
4. Freeze candidate variables, controls, test families, statistical methods, uncertainty estimates, multiplicity correction, and rejection criteria.
5. Define temporal validation and robustness checks before inspecting experiment results.
6. For Direct Monetization, specify realistic costs, liquidity, slippage, turnover, capacity, and net-value benchmark.
7. For Risk Control, specify an economically meaningful baseline and ensure the result is not merely caused by reducing exposure/capital deployment.
8. Obtain user approval of the research design before implementation.
9. Implement only the approved experiment, report execution provenance, and publish compact aggregate results under `docs/research/hypothesis_research/results/`.
10. Update hypothesis status only from the evidence; distinguish supported, rejected, and inconclusive outcomes.

Recommended first research design: DM-001 (relative-return persistence). RC-001 is the parallel foundational risk-control candidate. This is a priority recommendation, not authorization to start coding.

## Closed stage

EDA2 blocks 1–7 are complete and interpreted. Consolidated descriptive findings:
`docs/research/eda2/results/compilation/EDA2_RESULTS_COMPILATION.md`

Do not reopen EDA2 blocks without explicit request or concrete material error. EDA2 findings are descriptive and do not establish predictive effects.

## Standing constraints

- Approval-gated workflow: plan → user approval → implementation → evidence → analysis → agreed checks → stage decision.
- Distinguish descriptive structure, association, predictive generalization, causal claims, and economic utility.
- Preserve PIT membership, instrument identity, temporal availability, missingness, and provenance.
- No lookahead, leakage, survivorship/selection bias, random temporal shuffling, or uncorrected multiple-testing fishing.
- No hypothesis is accepted solely on historical profitability or statistical significance.
- Risk Control and Direct Monetization must not be conflated.
- No BUY/SELL, trading strategy, portfolio allocation, or live execution is produced by Stage 05.
- Never claim local execution based on GitHub inspection.
- Keep raw datasets, SQLite, Parquet, and bulky intermediate outputs out of GitHub.
