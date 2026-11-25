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

**CLOSED on 2026-11-25.** The experiment covered rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240 sessions. Do not reopen without explicit request or concrete new evidence.

## PIT TOP50 EDA: current understanding

First EDA run (user-executed 2026-11-25):
- 203,403 PIT membership rows; 214 SECIDs; 5,490 panel dates; 5,740 TQBR/EQBR calendar sessions.
- 199,169 rows marked bar-available (97.918%); 4,234 membership rows without a selected board bar.
- 197,955 valid positive adjusted-Close starting observations.
- Average daily membership 37.05; early years have fewer constituents, reaching an average of 50 from 2015.
- Panel Close matched selected adjusted SQLite Close on all 197,955 comparable observations at tolerance 1e-8.
- Future endpoint coverage at +1/+5/+20 sessions: 99.682% / 99.406% / 98.574%.
- Return distributions are heavy-tailed; pooled arithmetic and log-return means differ materially at +20. Annual summaries vary.
- This first pass was preliminary. It did not study serial dependence, cross-sectional dependence, date-level dispersion, instrument heterogeneity, rank mobility, or activity concentration. Do not call substantive EDA complete.

Known issues are not open research investigations:
- 1,214 incomplete bars are caused by a known refresh defect: incomplete history rows are not replaced with same-day MOEX candle data. Repair via a standalone overlay utility; raw SQLite remains append-only.
- One BELU quarantined row is known; no separate investigation is needed.

Active next research proposal: `docs/research/eda/EDA_V2_PLAN.md`. It covers distribution geometry, temporal dependence, cross-sectional co-movement, dispersion, instrument heterogeneity, PIT membership/rank mobility, and activity concentration. Await user approval before implementation.

## Incomplete-bar repair architecture

- Raw SQLite remains append-only and read-only to the repair utility.
- Standalone script `scripts/dataset/06_repair_incomplete_bars.py` fetches exact daily MOEX candles for raw keys with NULL OHLC and validates complete OHLC.
- Corrections are stored in `data/interim/bar_repairs/moex_candle_repairs.sqlite`.
- Adjusted builder applies overlay values at rebuild time and records repair provenance in derived data.
- Code is committed but not yet run against the user's local database. No runtime success claim is valid until the user runs it and shares results.

## Research boundaries

No fixed target, label, model count, or prediction horizon is selected. No feature engineering, IC leaderboard, model fitting, walk-forward evaluation, trading rules, or portfolio metrics during EDA. Descriptive conditional distributions can generate hypotheses but are not predictive evidence.

No forward-fill, synthetic bars, bridging missing sessions, automatic outlier deletion, or source-data mutation. Preserve PIT membership and missingness. Portfolio metrics remain prohibited until a final model is approved.
