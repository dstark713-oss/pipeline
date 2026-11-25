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


## 2026-11-25 | Rolling Statistical Moments closed; next OHLC family proposed

The user explicitly closed the Rolling Statistical Moments stage and instructed the Research Agent to stop repeatedly revisiting its 16 candidates. This closure is a workflow decision: do not reopen the feature family, repeat its IC/correlation/conditional-information discussion, or propose additional diagnostics without an explicit user request or concrete new evidence.

### Current role reaffirmed

The assistant's role in this workstream is **Researcher**. It identifies capability gaps, proposes research directions, teaches the underlying methods, designs falsifiable experiments, challenges assumptions, and documents evidence and limitations. It does not make trading/allocation decisions and does not optimize portfolio outcomes.

### Research plan preserved

For each new feature family:
1. Theory, intuition, mathematics, and interpretation.
2. Falsifiable hypotheses and failure modes.
3. Agree exact formulas, edge cases, sample rules, and evaluation parameters before execution.
4. Implement a reproducible experiment after specification approval.
5. Evaluate coverage, information content, temporal stability, redundancy, and uncertainty.
6. Record results and limitations; do not auto-promote features.
7. Recommend the next research capability.

The active prediction task and evaluation firewall remain unchanged: PIT TOP50, binary adjusted-Close direction t to t+5, features available by close t, expanding WF with 3-year initial training and monthly retraining, purge labels crossing the cutoff; no portfolio metrics before final model approval and only one decisive portfolio run after approval.

### Next feature-family proposal: OHLC price-formation decomposition

Proposed next investigation:
- Overnight gap: ln(Open_t / Close_{t-1}).
- Intraday return: ln(Close_t / Open_t).
- High-low log range: ln(High_t / Low_t).
- Close location value: (2*Close_t - High_t - Low_t)/(High_t-Low_t), with explicit zero-range handling.
- Upper/lower wick proportions, with exact non-duplicative formulas to be agreed.

Research question: do overnight repricing, intraday movement, and close location within the daily range contain distinct information about the five-session direction target?

This is a proposal only. Before coding, inspect adjusted OHLC consistency and data-quality constraints, teach the mathematics, agree definitions and edge cases, and freeze the specification. No claim is made that these features are predictive.

No new experiment was implemented or run as part of this decision. No project Python code was changed.


## 2026-11-25 | Correction: DS-first feature research constraint

The prior proposal to investigate OHLC gap/intraday/range/CLV/wick decomposition is withdrawn. The user reiterated that the new ML predictor must not use trader-style technical indicators/features and that the project must be approached through data science rather than trading conventions. The OHLC decomposition proposal drifted toward trader-style price-action feature engineering and was not appropriate.

Binding constraint clarified:
- Feature discovery must be grounded in statistics, statistical learning, probability, information theory, and time-series analysis.
- Do not use ATR, RSI, MACD, Bollinger Bands, stochastic oscillators, candlestick patterns, or trader-style price-action heuristics as candidate features or methodological templates.
- Do not disguise trading indicators with statistical names.
- OHLCV is a raw data source, not a mandate to derive trader signals.
- The legacy ATR-based tool is separate and is not a precedent for the new predictor.

The prior discussion identified Statistical Learning under Uncertainty as a broader methodological direction: weak signals, dependence between observations, uncertainty, and unstable/nonstationary distributions. A possible next research question is temporal dependence in the return-generating process (autocovariance/autocorrelation, partial dependence, estimation uncertainty, lag selection, and nonstationarity). This remains a proposal, not an approved feature family or experiment.

The next conversation must teach and scope the statistical question before selecting features or coding. No implementation or experiment was run for the withdrawn OHLC proposal.


## 2026-11-25 | Research workflow and context architecture approved

The user approved a mandatory stage-by-stage Data Science research workflow.

### Binding workflow

For every stage:
1. Research Agent proposes a plan.
2. User approves the plan.
3. Research Agent implements the approved scope in GitHub.
4. Compact, decision-relevant outputs required for analysis are saved under the appropriate `docs/` path. Do not upload thousands of CSV rows or bulky raw/intermediate data; prefer concise Markdown summaries, tables, aggregates, and diagnostics.
5. Research Agent analyzes the evidence and reports findings.
6. Necessary tests and checks are proposed and agreed with the user.
7. Agreed checks are implemented/run, and both code and actual results are reported with execution provenance.
8. Stage status is decided; the next stage is proposed using the previous stage's evidence and decisions, then approved before implementation.

At the end of the full research cycle, deliver a consolidated account of findings, supported/rejected/unresolved hypotheses, limitations, completed checks, reusable knowledge, and the next research plan.

### Context file architecture

The Research Agent context is separated into:
- `01_ROLE_AND_RULES.md`: role, boundaries, permissions, hard methodological rules.
- `RESEARCH_WORKFLOW.md`: mandatory stage protocol.
- `00_CUMULATIVE_KNOWLEDGE.md`: concise reusable knowledge across completed research cycles.
- `RESEARCH_JOURNAL.md`: chronological decisions, corrections, and stage events.
- Project-specific files such as `06_ML_DIRECTION_FEATURE_RESEARCH.md`: active project specifications and detailed stage context.
- `README.md`: navigation and source-of-truth index.
- `CHANGELOG.md`: concise context maintenance history.

Avoid duplication; maintain canonical placement and update the index when the structure changes.

### Implementation boundary

The protocol does not authorize unapproved scope changes. Plan approval authorizes only the implementation explicitly described in that plan. Runtime checks must not be reported as passed without actual execution output. GitHub inspection is not execution.

## 2026-11-25 | EDA approved and implemented

The user approved descriptive EDA with these corrections:
- The general structure/quality audit is already complete and must not be repeated.
- `numtrades` is absent from the current EDA data contract and is excluded.
- Future adjusted-close behavior is described at +1, +5, and +20 market sessions. These are exploratory horizons, not a selected target or model specification.
- The research must not assume a single model, a binary label, or even that a predictive model is warranted.

Committed the EDA implementation under `scripts/experiments/ml_1/eda/` and its approved scope under `docs/research/eda/EDA_SPEC.md`. Updated the canonical ML research specification, next steps, cumulative knowledge, repository index, and panel field description to remove the stale fixed t-to-t+5 target and walk-forward assumptions.

Implementation is code-inspected but not run here. The user will pull, execute against local Parquet/SQLite data, and push compact outputs under `docs/research/eda/` for analysis. No runtime findings are available yet.


## 2026-11-26 | EDA results reviewed; targeted validation proposed

The user ran the approved EDA locally and committed the generated outputs to `main`. The run metadata records 2026-11-25 18:51 UTC, code revision `46fb41a8a289609313c06defce2ec3f72c1e500e`, Python 3.12.7, pandas 3.0.2, and NumPy 2.4.4.

### Dataset snapshot

- 203,403 PIT membership rows; 214 SECIDs; 5,490 dates from 2005-01-11 to 2026-11-25.
- Full TQBR/EQBR market calendar: 5,740 sessions.
- 199,169 rows with `bar_available=1` (97.918%); 4,234 membership rows have no board bar.
- 197,955 valid positive adjusted-Close observations form the future-price starting cohort.
- Daily membership averaged 37.05. Early history had substantially fewer than 50 members; average membership reached 50 from 2015 onward. Bar coverage was notably lower in 2006 (83.52%) and 2011 (76.91%).

### EDA findings

- Pooled adjusted-price, Volume, and Value levels are strongly right-skewed/heavy-tailed; pooled moments are descriptive only and mix instruments, scales, and periods.
- Among 197,955 complete OHLC observations, checked price-order constraints had zero violations; non-positive adjusted prices were not found among non-missing values.
- Panel Close matched selected adjusted SQLite Close on all 197,955 comparable rows at tolerance 1e-8.
- The OHLC completeness check reports 1,214 incomplete rows among 199,169 bar-available rows; separate checks each report 1,214 missing panel Close and selected-history Close values. Row-level overlap is not established by the aggregate report. Clarify the semantics of `bar_available`.
- Selected board shares: TQBR 81.56%, EQBR 18.44%; one row is flagged `QUARANTINED_MIXED_SCALE`, but aggregate outputs do not identify it.
- Exact endpoint coverage at +1/+5/+20 sessions: 99.682% / 99.406% / 98.574%.
- Positive/negative/zero return shares are close to balanced. At +5 they are 49.46% / 49.99% / 0.55%; at +20, 50.43% / 49.34% / 0.23%.
- Returns are heavy-tailed and annual summaries vary materially. At +20 the mean simple return is +0.521%, while mean log return is -0.165%; this reflects distribution asymmetry and must not be interpreted as a forecast edge.
- No inference, IC, feature-target association, model fitting, WF evaluation, or portfolio metrics were computed.

### Decisions and next work

EDA is reviewed. The next proposed stage is targeted diagnostics: classify the 1,214 incomplete bars and verify `bar_available`; trace the quarantined mixed-scale row; trace extreme future returns to exact source observations; test calendar endpoint/return calculations and PIT cohort semantics; characterize the 4,234 no-board rows, especially 2006 and 2011.

These checks are proposed and await user approval. Do not implement them or move to prediction-problem design before scope approval and validation. No target, label, model, feature family, or forecast horizon is selected.

During this review, the active ML research memory file was found to contain unresolved Git conflict markers and stale fixed-target/OHLC-feature instructions. It has been replaced with a clean current specification; superseded instructions were removed rather than retained.


## 2026-11-26 | EDA direction corrected; repair overlay implemented

The user clarified that the 1,214 incomplete bars are a known refresh defect: same-day MOEX candles can be retrieved, but the refresh process does not replace existing incomplete history rows. The user authorized a separate repair script, explicitly not a refresh-pipeline modification. The raw SQLite database must remain append-only; corrections are stored in a separate overlay. The single BELU quarantined row requires no additional investigation.

Implemented and committed:
- `scripts/dataset/06_repair_incomplete_bars.py`: selects raw SECID/BOARDID/TRADEDATE keys with NULL OHLC, requests exact daily candles from MOEX ISS, validates full OHLC, and writes a provenance-bearing overlay.
- `data/interim/bar_repairs/moex_candle_repairs.sqlite`: local runtime overlay path; database itself is not committed.
- `scripts/dataset/04_build_adjusted_dataset.py`: applies overlay values when rebuilding adjusted data and records repair ID/fetch timestamp in derived output.
- `scripts/dataset/tests/test_incomplete_bar_repair.py`: offline unit tests for candle validation, candidate grouping, and idempotent overlay upsert.
- `scripts/dataset/README.md`: run instructions.

Implementation is code-inspected but has not been run against the user's local raw SQLite. Runtime correctness remains unverified.

The user correctly objected that the first EDA pass had devolved into repeated data-quality audits and had not studied the statistical behaviour of the TOP50 panel. The previous targeted-audit follow-up was withdrawn. Added `docs/research/eda/EDA_V2_PLAN.md` for substantive analysis of return distributions, temporal dependence, cross-sectional dependence, date-level dispersion, instrument heterogeneity, PIT rank/membership mobility, and activity concentration. The plan is proposed and awaits approval; no EDA v2 code has been implemented.
