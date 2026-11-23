# Next Steps and Open Risks

Last updated: 2026-11-23

## Active project: ML direction prediction

<decision>Approved by the user on 2026-11-23.</decision>

Build and validate an ML model that predicts the direction of price movement for individual instruments.

The initial research motivation is the earlier observation that an instrument's position within its own recent price range may contain information about the conditional distribution of future returns. This is a starting hypothesis to test, not a proven predictive relationship. Do not confuse it with the statistical null hypothesis.

The first stage is research design, not immediate model fitting. Settle and document:

1. Prediction target and label construction (including treatment of near-zero returns and ambiguous cases).
2. Forecast horizon or horizons and why they are relevant.
3. Eligible instrument universe and point-in-time availability rules.
4. Feature candidates, beginning with the range-position hypothesis and existing screener primitives, without assuming all are useful.
5. Simple statistical and ML baselines.
6. WF temporal evaluation design, leakage controls, metrics, aggregation, and failure criteria.
7. Reproducibility requirements and experiment registry fields.

Do not begin broad feature fishing or complex model search before these definitions are fixed.

## Mandatory evaluation firewall

The user explicitly prohibited portfolio-level metrics before approval of the final model.

- Before final model approval, do not inspect, calculate, report, compare, or use any portfolio-level metrics or portfolio application results.
- This includes portfolio CAGR, Sharpe, MDD, returns, drawdowns, exposure, turnover, and related portfolio outputs.
- Statistical and predictive-model metrics on WF are allowed.
- The user will not split the dataset into separate fixed IS and VAL subsets. Do not require or introduce such a split.
- Use WF as the permitted statistical/model evaluation procedure. Specify its temporal construction and leakage safeguards before examining results.
- After the final model is approved, exactly one decisive portfolio-level evaluation run is permitted.
- Do not iterate, tune, compare portfolio variants, or select model settings based on that one portfolio run. It is a downstream application check, not a feedback loop.

This firewall applies to all research-agent work, scripts, reports, and discussions for this project. If an existing artifact contains portfolio metrics, do not open or inspect those metrics during model development.

## Research sequence

1. **Formalize the prediction problem.** Define what “up” and “down” mean, horizon, label timestamp, forecast timestamp, and handling of neutral/ambiguous outcomes.
2. **Establish baselines.** Quantify simple unconditional and conditional distributions and transparent baseline predictors, including the range-position hypothesis.
3. **Build the modeling dataset.** Ensure each feature is available at prediction time; preserve point-in-time universe membership and instrument identity; document missingness and sample eligibility.
4. **Develop candidate models.** Start with interpretable/simple models before increasing complexity. Keep feature selection and tuning inside the predeclared WF process.
5. **Evaluate statistically on WF.** Use suitable classification/distribution metrics, uncertainty estimates, calibration diagnostics where relevant, and robustness by time period/instrument cohort. No portfolio metrics.
6. **Freeze and document the final candidate.** Record model specification, feature set, target, horizon, WF evidence, limitations, and reproducibility details.
7. **Obtain user approval.** No portfolio-level evaluation before explicit approval of the final model.
8. **Run one decisive portfolio application evaluation.** Do not use its result to revise the model or run a second portfolio variant.

## Current information layer

- Instrument state: `drawdown_60`, `zscore_sma20_20`, `realized_vol_60`.
- Separate market-state context: `breadth_change_5` (primary) and `breadth_sma20` (reference).
- Screener: `scripts/tools/01_primitive_screener.py`.
- Downstream specification: `docs/tools/01_primitive_screener.md`.

The screener is descriptive only. It does not generate trades, portfolio weights, or allocation instructions.

## Data reality and constraints

- The repository contains an internal historical market-data pipeline. Its exact coverage and limitations are recorded in `02_DATASET_PIPELINE.md`.
- There is **no internal fundamental-data dataset or fundamental-data pipeline**.
- News, company context, market semantics, and fundamental information are retrieved from the internet/external sources in the agent workflow.
- Current web retrieval is not equivalent to a persistent, timestamped historical dataset. Do not use present-day information to support historical point-in-time claims.
- Do not add external semantic/fundamental features to the direction model by assumption. They require a separate data-availability, timestamp, provenance, and leakage assessment, and must fit the approved prediction problem.

## Retired proposal

The previous proposal to make conditional downside-risk analysis across breadth regimes the immediate next research project is not the current plan. It was a premature continuation of the previous breadth topic. Do not resume it unless the user explicitly reprioritizes it.

## Dataset and operational risks

- Verify the refresh script locally before relying on it.
- Resolve delayed publication after an empty MOEX response, calendar-yesterday cutoff, and missing SECID/board-pair onboarding.
- Do not rebuild completed historical-universe/raw/audit/adjustment stages without a concrete defect.
- Keep raw observations immutable and derived datasets rebuildable.
- Do not claim local execution or validation from GitHub code inspection alone.

## Research discipline

- No broad feature fishing.
- Do not optimize model selection or feature design against portfolio metrics.
- Statistical WF evaluation is permitted; portfolio evaluation is gated as above.
- Preserve failed and inconclusive experiments as useful evidence.
- The Research Agent recommends; the user approves scope changes and final model approval.
