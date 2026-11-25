# ML Research: EDA Findings and Current Direction

Last updated: 2026-11-26

## Objective and methodological rules

Use the PIT TOP50 MOEX daily panel to understand statistical structure and decide which research problems, if any, are justified. Do not assume a predictive model is necessary, or preselect a single target, horizon, or model.

Use a DS-first lens: statistics, probability, information theory, time-series analysis, statistical learning, uncertainty, heterogeneity, and nonstationarity. No trader-style indicators, technical signals, candlestick patterns, or price-action heuristics (including ATR, RSI, MACD, Bollinger Bands, stochastic oscillators, and disguised equivalents).

No feature selection, IC leaderboard, model fitting, walk-forward validation, trading rules, or portfolio metrics during EDA. Descriptive conditional distributions may be used for hypothesis generation, not presented as predictive evidence.

## First EDA pass: results and limitations

Canonical specification: `docs/research/eda/EDA_SPEC.md`  
User-run report: `docs/research/eda/EDA_REPORT.md`  
Researcher's review: `docs/research/eda/EDA_ANALYSIS.md`

The user ran EDA locally on 2026-11-25 using code revision `46fb41a8a289609313c06defce2ec3f72c1e500e`, Python 3.12.7, pandas 3.0.2, NumPy 2.4.4. Outputs are committed to main. The Research Agent reviewed committed outputs but did not independently execute the run.

Snapshot:
- 203,403 PIT membership rows; 214 SECIDs; 5,490 panel dates (2005-01-11 to 2026-11-25).
- Full TQBR/EQBR calendar: 5,740 sessions.
- 199,169 rows marked bar-available (97.918%); 4,234 membership rows without a selected board bar.
- 197,955 valid positive adjusted-Close starting observations.
- Mean daily membership 37.05; early years have fewer constituents, reaching an average of 50 from 2015.
- Bar coverage is lower in 2006 (83.52%) and 2011 (76.91%).

Findings:
1. Pooled adjusted Close, Volume, and Value levels are strongly right-skewed/heavy-tailed. These pooled moments mix instruments, scales, and periods and do not characterize a homogeneous variable.
2. On 197,955 comparable observations, panel Close matched selected adjusted SQLite Close at tolerance 1e-8. Checked OHLC ordering constraints had zero violations on complete bars.
3. The 1,214 incomplete bars are a known refresh-pipeline defect: the refresh process does not replace incomplete history rows with complete same-day MOEX candle data. This is understood, not an open EDA investigation.
4. One BELU quarantined row is known and intentionally not a separate work item.
5. Exact future endpoint coverage at +1/+5/+20 sessions is 99.682% / 99.406% / 98.574%.
6. Direction shares at +1/+5/+20 are close to balanced. At +20 mean simple return is +0.521%, while mean log return is -0.165%; return distributions are heavy-tailed and annual summaries vary.
7. These are descriptive pooled summaries only. Serial dependence, cross-sectional dependence, dispersion dynamics, instrument heterogeneity, rank mobility, uncertainty, and multiplicity were not studied.

The first EDA pass is therefore **not a completed substantive EDA**. Its report is a preliminary descriptive/consistency pass. The previous proposal to spend the next stage on repeated source audits is withdrawn.

## Active engineering task: incomplete-bar repair overlay

The raw SQLite database remains append-only. A standalone utility has been added:
- `scripts/dataset/06_repair_incomplete_bars.py`
- Unit tests: `scripts/dataset/tests/test_incomplete_bar_repair.py`
- Usage: `scripts/dataset/README.md`

It identifies distinct SECID/BOARDID/TRADEDATE keys with NULL OHLC fields in raw SQLite, requests exact daily candles from MOEX ISS, validates complete OHLC, and writes corrections to `data/interim/bar_repairs/moex_candle_repairs.sqlite`. It never modifies raw SQLite.

The adjusted builder `scripts/dataset/04_build_adjusted_dataset.py` now reads the optional overlay and applies its values while rebuilding adjusted data. It records `bar_repair_id` and `bar_repair_fetched_at_utc` in the derived table. The repair utility and builder integration are committed but **not runtime-tested on the user's local database**. User must pull, run a small dry-run, then perform the repair and rebuild; results must be inspected before declaring success.

Commands:
```powershell
python scripts/dataset/06_repair_incomplete_bars.py --dry-run --limit 10
python scripts/dataset/06_repair_incomplete_bars.py
python scripts/dataset/04_build_adjusted_dataset.py
python -m unittest discover -s scripts/dataset/tests -v
```

## Next research stage: EDA v2

Proposed plan: `docs/research/eda/EDA_V2_PLAN.md`. This is a plan only; implementation has not started and requires user approval.

EDA v2 should investigate:
1. Return distribution geometry: per-security, pooled/equal-security-weighted, tail asymmetry, quantiles, annual/rolling variation.
2. Temporal dependence: ACF of signed returns, absolute returns, squared returns; per-security Ljung-Box with minimum sample sizes and BH correction.
3. Cross-sectional dependence: pairwise correlations, rolling dependence, covariance eigenvalue concentration, exploratory PCA.
4. Date-level cross-sectional dispersion: median, MAD, IQR, standard deviation, positive/negative shares, persistence.
5. Instrument heterogeneity: between- and within-security scale/shape differences, rolling dispersion.
6. PIT membership and rank mobility: tenure, entries/exits, persistence, rank transition matrices.
7. Activity concentration and descriptive stratification by PIT rank/Value/Volume, without IC rankings or predictive claims.

Statistical inference must respect serial and cross-sectional dependence, use dependence-aware uncertainty where appropriate, correct repeated test families, and report effect sizes/sample sizes alongside p-values.

The known incomplete-bar problem and single BELU quarantined row are not EDA research tasks. Missingness may be described only when needed to understand population/sample composition.

## Completed prior research

- Log returns: `r_t = ln(P_t / P_{t-1})` are additive across consecutive periods and scale-normalized, but do not guarantee stationarity.
- Rolling Statistical Moments: **CLOSED on 2026-11-25**. Do not reopen absent explicit request or concrete new evidence.

## Binding boundaries

- Preserve PIT membership, SECID identity, market-session timing, and missingness.
- Never forward-fill, create synthetic bars, bridge missing sessions, or automatically delete outliers.
- `numtrades` is absent from the current EDA data contract.
- No target, label, model count, or prediction horizon is currently selected.
- No portfolio metrics before final model approval; after approval, only the separately authorized decisive portfolio-level run.
- Repository inspection is not execution. Distinguish committed code from runtime-verified behavior.
- Keep canonical memory current; replace superseded decisions instead of accumulating contradictory history.
