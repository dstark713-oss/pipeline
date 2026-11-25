# Next Steps and Open Risks

Last updated: 2026-11-26

## Active stage: targeted EDA diagnostic validation

**Status:** EDA implementation and local run are complete; report reviewed; targeted checks proposed and awaiting user approval.

- Approved EDA specification: `docs/research/eda/EDA_SPEC.md`.
- Generated descriptive report: `docs/research/eda/EDA_REPORT.md`.
- Research analysis: `docs/research/eda/EDA_ANALYSIS.md`.
- Implementation: `scripts/experiments/ml_1/eda/`.

Key findings:
- 203,403 membership rows; 214 SECIDs; 5,490 panel dates; 5,740 market-calendar sessions.
- Overall `bar_available` coverage 97.918%; 4,234 PIT rows have no board bar.
- The OHLC completeness check reports 1,214 incomplete bar-available rows; separate checks each report 1,214 missing panel Close and selected-history Close values. Row-level overlap is not established by the aggregate report. Clarify flag semantics.
- Panel Close matches selected adjusted SQLite Close on all 197,955 comparable observations.
- Future endpoint coverage is 99.682% / 99.406% / 98.574% at +1/+5/+20.
- Pooled returns are heavy-tailed and annual distributions vary; no target or model is selected.

## Proposed checks, pending approval

1. Characterize 1,214 incomplete bars by year, SECID, board, and missing OHLC field; clarify `bar_available`.
2. Identify and trace the one `QUARANTINED_MIXED_SCALE` row to source/action provenance.
3. Trace extreme future returns by horizon to exact SECID, signal date, endpoint date, and adjusted-history rows.
4. Add/run unit tests for exact +1/+5/+20 calendar offsets, return formulas, missing endpoints, and PIT signal-date cohort semantics.
5. Characterize 4,234 no-board rows, with special attention to 2006 and 2011.

No generic structure/quality audit is to be repeated. No source mutation, automatic outlier deletion, feature engineering, IC, target selection, model fitting, WF evaluation, or portfolio metrics.

## After validation

Use the verified diagnostics to decide whether to design a prediction problem at all. Any target/outcome, horizon, sample eligibility, baseline, leakage controls, validation, and evaluation protocol must be separately proposed and approved before implementation. The project may require multiple models or no predictive model.

## Completed prior research

- Log returns: base statistical representation documented.
- Rolling Statistical Moments: **CLOSED** on 2026-11-25. Do not reopen without explicit request or concrete new evidence.

## Standing constraints

- DS-first methods only; no trader-style indicators or disguised price-action heuristics.
- Preserve PIT membership, SECID identity, actual market-session timing, and missingness.
- No forward-fill, synthetic observations, automatic outlier deletion, or source-data mutation.
- No portfolio metrics before final model approval.
- Keep raw datasets, SQLite, Parquet, and row-level exports out of GitHub.
- Runtime claims require actual execution evidence; GitHub inspection is not execution.
