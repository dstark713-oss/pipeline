# Next Steps and Open Risks

Last updated: 2026-11-25

## Active stage: descriptive EDA

**Status:** approved scope; implementation committed; awaiting user-run results.

- Specification: `docs/research/eda/EDA_SPEC.md`.
- Code: `scripts/experiments/ml_1/eda/`.
- Run from repository root: `python scripts/experiments/ml_1/eda/run_eda.py`.
- Outputs: compact aggregate reports under `docs/research/eda/`.
- User will pull the code, execute locally against Parquet/SQLite, and push the generated outputs for review.

EDA scope: temporal coverage and PIT membership dynamics; distributions of adjusted OHLC, volume, value, value_60d, rank, and universe_size; annual/instrument heterogeneity; internal consistency diagnostics; descriptive Close[t] to Close[t+1/5/20] behavior.

The 1/5/20 horizons are exploratory descriptive comparisons only. No target, label, model family, or final forecast horizon is selected. `numtrades` is absent from the current EDA data contract and is excluded.

## Completed prior research

- Log returns: base statistical representation documented.
- Rolling Statistical Moments: **CLOSED** on 2026-11-25. Do not reopen without explicit user request or concrete new evidence.

## After EDA

Review the user-generated report and decide from evidence whether a prediction problem is justified. Only then propose a separate prediction-problem design covering outcome definition, horizon(s), eligible observations, baselines, leakage controls, validation, and evaluation. The system may require multiple models or no predictive model at all.

Do not begin feature engineering or model implementation before that design is explicitly approved.

## Standing constraints

- DS-first methods only; no trader-style indicators or disguised price-action heuristics.
- Preserve PIT membership, SECID identity, actual market-session timing, and missingness.
- No forward-fill, synthetic observations, automatic outlier deletion, or source-data mutation.
- No feature-target association, IC, model fitting, WF evaluation, or portfolio metrics during the current EDA.
- Keep raw datasets, SQLite, Parquet, and row-level exports out of GitHub.
- Repository inspection is not execution; do not claim runtime success without actual output.
