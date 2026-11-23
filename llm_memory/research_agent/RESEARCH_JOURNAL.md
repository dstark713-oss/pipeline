# Research Agent Journal

This is the Research Agent's own chronological research log. It is separate from the user's daily_report.txt, which must remain user-owned and unmodified.

## 2026-11-23 | Repository review and next research proposal

### Sources reviewed

- User journal: daily_report.txt, entries dated 2026-11-22 and 2026-11-23.
- Research Agent context: README.md, 01_ROLE_AND_RULES.md, 02_DATASET_PIPELINE.md, 03_PRIMITIVE_RESEARCH.md, 04_REFRESH_MECHANISM.md, 05_NEXT_STEPS.md, CHANGELOG.md.
- Tool documentation: docs/DATASET_PIPELINE.md, docs/tools/00_refresh_ds.md, docs/tools/01_primitive_screener.md.
- Research implementations: primitive discovery, decile/period/rolling stability, correlation and incremental breadth scripts; breadth market-structure analysis; portfolio application simulator and audit scripts.

Repository inspection is not local execution. Local generated research outputs under data/ were not available through the inspected GitHub tree. Conclusions below distinguish committed implementation from user-reported findings.

### Current research state

The user's diary records:
- 2026-11-22: the practical need for a deterministic state-information tool for an existing portfolio, rather than rushing an overnight ML strategy; initial primitive IC observations.
- 2026-11-23: decile and correlation diagnostics; the selected instrument-level dimensions are distance from 60-session highs, z-score relative to SMA20, and realized volatility. Breadth was separated from instrument-level features because its dynamic change carries a distinct market-state layer.

Current production information layer:
- Instrument primitives: drawdown_60, zscore_sma20_20, realized_vol_60.
- Separate breadth context: breadth_change_5 and reference level breadth_sma20.
- Runtime tool: scripts/tools/01_primitive_screener.py.
- Downstream instructions: docs/tools/01_primitive_screener.md.

### Methodological decisions to preserve

- This is information research, not classical strategy construction or return optimization.
- The screener describes instrument and market states; it does not issue BUY/SELL/HOLD, generate composite scores, or set portfolio weights.
- The three instrument primitives and breadth remain separate information dimensions.
- Breadth's 100/75/50/25% sizing schedule is the user's heuristic. It is not a statistically estimated or optimized allocation rule. The user observed lower drawdown directionally in the tested portfolio application; treat this as an experiment-specific observation, not causal or universal proof.
- Portfolio metrics are diagnostics of an application construction, not truth criteria for an information effect.
- Preserve PIT membership, no forward-fill, missingness as missing, and SECID as distinct instrument identity. Never merge SECIDs by issuer or ISIN without explicit rules.

### Audit findings

1. Screener documentation still stated that the realized_vol_60 TOP 15 was sorted descending. The implementation had already been corrected to ascending, from lowest to higher volatility. Documentation was updated.
2. The approved breadth rule places breadth_sma20 >= 50% in the upper regime. The portfolio test implementation currently uses breadth_level > 50.0; exactly 50% is classified into the lower regime. This is a specification/implementation mismatch. Code was not changed during this review.
3. The current portfolio simulator uses signal after close T, entry at OPEN T+1, and exit/rebalance at OPEN T+2. Its committed code can be inspected, but this review does not establish a fresh local run or independent execution validation.
4. The refresh mechanism still has documented operational limitations: no onboarding/backfill for SECID/board pairs absent from raw data, cutoff based on calendar yesterday, and a successful empty response can advance a checkpoint despite possible late publication. Runtime validation remains user-run pending.
5. The old next-steps memory incorrectly described the screener as deferred. The screener is already committed; context was updated.

### Recommended next direction: conditional downside-risk information in breadth regimes

Question: Do the four predeclared breadth regimes contain stable incremental information about the future downside-risk distribution of the signal-date PIT TOP50 cohort, beyond recent cohort returns and the cross-sectional medians of the three approved instrument primitives?

Use the user's existing regime map without tuning:
- breadth >= 50%, change > 0;
- breadth >= 50%, change <= 0;
- breadth < 50%, change > 0;
- breadth < 50%, change <= 0.

Focus on risk-state outcomes over 5/10/20 sessions: lower-tail cohort returns, negative-return share, cross-sectional 10th percentile / worst-decile expected shortfall, and downside semivariance or forward downside volatility. Consider maximum adverse excursion only if it can be defined cleanly from adjusted OHLC and predeclared before analysis.

Use signal-date PIT cohorts, report regime counts and coverage, control for past cohort returns and core primitive medians, use dependence-aware inference (HAC / block bootstrap), correct declared multiple-testing families, and report established subperiods 2005-2012, 2013-2019, 2020-2026. Do not optimize the 50% threshold or 100/75/50/25% multipliers.

This is the recommended next study because existing breadth research already covered average/median forward returns, positive share, incremental return associations, and market structure. The unresolved question most relevant to the user's allocation heuristic is whether breadth regimes distinguish future downside risk and left-tail behavior.

A positive result would support breadth as a risk-state context for downstream allocation decisions, not validate exact multipliers or make the screener a strategy. A negative/unstable result would weaken the risk-classification claim but would not erase breadth's descriptive role.

### Status

- Repository and committed research code reviewed.
- User diary reviewed; left unchanged.
- Documentation and agent memory maintenance changes made.
- Next research proposal is pending user approval.
- No new experiment code was written or run.


## 2026-11-23 | Research Agent role correction and screener research closure

The user clarified the intended role by reference to Microsoft's R&D-Agent-Quant architecture: this agent is the research/development side of a larger system. The separate Trading Agent is a downstream consumer of new analytical capabilities and is out of scope for this role definition.

### Role decision

The Research Agent is an autonomous researcher and developer of validated analytical capabilities for financial-market analysis. Its work includes identifying capability gaps, formulating hypotheses, designing experiments, building data interfaces/datasets/methods/models/tools, validating them, documenting limitations, and delivering reusable capabilities to the Trading Agent.

The output is an analytical capability or validated knowledge, not a trade, allocation, or trading strategy.

### Research-stage status

- The first primitive research cycle is closed.
- The hypothesis of constructing a market-state screener from selected primitives is closed.
- The screener is the first runtime tool produced by the research process, not the permanent research boundary.
- The next cycle begins with a capability audit: what the screener and existing data make possible, what remains unknown or unreliable, and which tools/data/methods close the highest-value gaps.
- The prior immediate proposal to continue breadth research through conditional downside-risk analysis is retired as premature. It must not be treated as the approved next project.

### Data constraint clarified by the user

There is no internal fundamental-data dataset or pipeline. The agent retrieves market semantics, news, company context, and fundamental information from the internet/external sources. External information therefore requires source and temporal provenance. A current web lookup must not be mistaken for point-in-time historical evidence.

### Repository maintenance

Updated the Research Agent role, directory index, and next-steps file to reflect these decisions. No Python/project code was changed. No Trading Agent files or user diary artifacts were changed.


## 2026-11-23 | Next research approved: ML direction prediction

The user selected ML prediction of price-movement direction as the next research project.

### Research motivation

The starting observation is that an instrument's position within its own recent price range may contain information about the conditional distribution of future returns. This is an initial hypothesis to investigate, not a proven result and not the statistical null hypothesis.

The research should establish a sound prediction problem and test whether candidate features add stable information. It must not jump directly from the observation to a complex model or assume a binary target is necessarily optimal without defining labels and horizons.

### Binding evaluation rule: portfolio-metric firewall

The user explicitly imposed a strict separation between model research and portfolio evaluation:

- No portfolio-level metrics may be inspected, calculated, reported, compared, or used before the final model is approved.
- This prohibition applies throughout dataset/target design, feature research, model development, feature selection, tuning, model comparison, and WF evaluation.
- Portfolio CAGR, Sharpe, MDD, returns, drawdowns, exposure, turnover, and other portfolio application outputs are all prohibited during this phase.
- Statistical and predictive-model metrics on walk-forward (WF) evaluation are permitted.
- The user will not split the dataset into separate fixed IS/VAL subsets. Do not introduce that as a project requirement.
- WF design, temporal boundaries, leakage controls, metrics, and aggregation must be defined before inspecting results.
- After the final model is approved, exactly one decisive portfolio-level run is permitted.
- The portfolio run is a downstream application check only. It must not be used for tuning, model selection, or further iteration; no repeated portfolio variants.

### Immediate next work

Begin by formalizing the prediction problem: label/target, horizon, prediction timestamp, neutral/ambiguous outcomes, eligible universe, baseline, WF design, statistical metrics, leakage controls, and failure criteria. Do not write or run model code until these are sufficiently specified.

### Status

- Direction-prediction research approved by the user.
- Portfolio-metric firewall recorded as a binding constraint.
- No model code or portfolio evaluation was run as part of this decision.
