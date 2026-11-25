# Next Steps and Open Risks

Last updated: 2026-11-26

## Active engineering task: repair incomplete daily bars

**Status:** implementation committed to main; local runtime validation pending.

The 1,214 incomplete bars are a known refresh-pipeline defect, not an open data-quality investigation. The refresh process may retrieve a same-day candle but does not replace an existing incomplete history row. Raw SQLite must remain append-only.

Added:
- `scripts/dataset/06_repair_incomplete_bars.py`
- `scripts/dataset/tests/test_incomplete_bar_repair.py`
- Overlay: `data/interim/bar_repairs/moex_candle_repairs.sqlite`
- Adjusted builder integration: `scripts/dataset/04_build_adjusted_dataset.py`

User run sequence:
```powershell
python scripts/dataset/06_repair_incomplete_bars.py --dry-run --limit 10
python scripts/dataset/06_repair_incomplete_bars.py
python scripts/dataset/04_build_adjusted_dataset.py
python -m unittest discover -s scripts/dataset/tests -v
```

Do not claim success until the user runs this against local data and shares the report. Check candidate count, repaired/unavailable/error counts, raw DB unchanged, overlay contents, and adjusted builder repair counts.

## Active research stage: substantive EDA v2

Proposed plan: `docs/research/eda/EDA_V2_PLAN.md`. Await user approval before implementing.

The previous "targeted diagnostic validation" proposal is withdrawn. Do not spend another cycle on the known 1,214 incomplete bars, the single BELU quarantined row, or generic no-board audits.

EDA v2 is intended to characterize statistical behaviour:
1. Return distribution geometry and tails.
2. Temporal dependence in signed and absolute/squared returns.
3. Cross-sectional dependence and common movement.
4. Date-level cross-sectional dispersion and breadth statistics.
5. Between-security heterogeneity and time-varying scale.
6. PIT membership tenure, turnover, and rank mobility.
7. Activity concentration and descriptive rank/activity stratification.

Use per-security/time summaries, dependence-aware inference, minimum sample sizes, effect sizes, uncertainty intervals, and multiplicity correction. No IC leaderboard, feature selection, model fitting, WF evaluation, trading rules, or portfolio metrics.

## Later

After EDA v2, review actual findings and formulate research hypotheses. Only then decide whether a prediction problem is justified, and separately design/approve its outcome, horizon, sample, baseline, leakage controls, validation, and evaluation.

## Completed prior research

- Log returns: base statistical representation documented.
- Rolling Statistical Moments: **CLOSED** on 2026-11-25.

## Standing constraints

- DS-first methods only; no trader-style indicators or disguised price-action heuristics.
- Preserve PIT membership, SECID identity, actual market-session timing, and missingness.
- No forward-fill, synthetic observations, automatic outlier deletion, or source-data mutation.
- No portfolio metrics before final model approval.
- Keep raw datasets, SQLite, Parquet, and row-level exports out of GitHub.
- Runtime claims require actual execution evidence; GitHub inspection is not execution.
