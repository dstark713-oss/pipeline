# ML Research: EDA Findings and Prediction-Problem Design

Last updated: 2026-11-26

## Project objective

Use the PIT TOP50 MOEX daily market dataset to determine which analytical or prediction problems, if any, are supported by the observed data. Do not assume one model, a binary target, a fixed horizon, or that a predictive model is necessary.

Methodology is DS-first: statistics, probability, information theory, time-series analysis, statistical learning, uncertainty, heterogeneity, and nonstationarity. Do not use trader-style indicators or price-action heuristics as feature templates. Explicit exclusions include ATR, RSI, MACD, Bollinger Bands, stochastic oscillators, and candlestick patterns. OHLCV is the raw observation domain, not a mandate to construct trading signals.

## Current stage: EDA reviewed; targeted validation pending

Canonical specification: `docs/research/eda/EDA_SPEC.md`  
Generated report: `docs/research/eda/EDA_REPORT.md`  
Researcher's interpretation: `docs/research/eda/EDA_ANALYSIS.md`  
Implementation: `scripts/experiments/ml_1/eda/`

The user ran the EDA locally on 2026-11-25 using code revision `46fb41a8a289609313c06defce2ec3f72c1e500e`, Python 3.12.7, pandas 3.0.2, and NumPy 2.4.4. The generated outputs are committed to `main`. This is user-run evidence, not an independent rerun by the Research Agent.

### Dataset snapshot from this run

- Panel: 2005-01-11 to 2026-11-25.
- 203,403 PIT membership rows, 214 SECIDs, 5,490 panel dates.
- Full TQBR/EQBR calendar: 5,740 sessions.
- 199,169 rows with `bar_available=1`; overall bar coverage 97.918%.
- 197,955 observations have positive adjusted Close at t and form the future-price starting cohort.
- Daily membership averaged 37.05; early years had substantially fewer than 50 members. The 5th percentile of daily bar coverage is 81.82%.

### Main descriptive findings

1. **Coverage and composition vary through time.** Average daily membership was roughly 10-17 in 2005-2009, 21 in 2010, 30 in 2011, and 50 from 2015 onward. Bar coverage was 83.52% in 2006 and 76.91% in 2011, versus near 99-100% in most recent years. Do not treat the panel as a constant 50-security cross-section over the full history.
2. **Pooled level distributions are extremely skewed and heavy-tailed.** Adjusted Close skewness is 17.74 with excess kurtosis 408.86; Volume skewness is 87.20 with excess kurtosis 10,755.3. These pooled statistics mix different securities, scales, and periods. They are diagnostics, not evidence that raw levels are useful features or that extreme values are errors.
3. **Most complete OHLC rows pass internal constraints.** On 197,955 complete OHLC rows, price ordering constraints have zero violations; non-positive adjusted prices were not found among non-missing values. Panel Close matches the board-selected adjusted SQLite Close on all 197,955 comparable rows at tolerance 1e-8.
4. **A bar-availability semantic issue remains.** 1,214 of 199,169 rows marked `bar_available=1` have incomplete OHLC; the same count is marked as missing adjusted Close and missing selected adjusted-history Close. Verify whether `bar_available` means source-row existence or usable-bar completeness before relying on it as an eligibility flag.
5. **Board/adjustment composition:** selected price board is TQBR for 81.56% and EQBR for 18.44% of available rows. There are 1,218 two-board rows, 4,234 no-board rows, and one `QUARANTINED_MIXED_SCALE` row. The aggregate output does not identify that row's SECID/date.
6. **Future endpoint coverage is high:** 99.682% at +1, 99.406% at +5, and 98.574% at +20 market sessions. Exact t+h endpoints on the full calendar are used; no interpolation or future TOP50 membership requirement is applied.
7. **Pooled direction shares are close to balanced.** Positive/negative/zero shares are 48.12/50.47/1.41% at +1, 49.46/49.99/0.55% at +5, and 50.43/49.34/0.23% at +20. These are descriptive realized shares, not forecasts.
8. **Return distributions are heavy-tailed and temporally heterogeneous.** At +20, simple-return mean is +0.521% while log-return mean is -0.165%; simple-return standard deviation is 11.76%. +20 log-return annual means range from -11.19% in 2008 and -4.00% in 2022 to +6.74% in 2009 and +3.04% in 2023. This is descriptive time variation, confounded by changing PIT cohort composition and dependence.

### Interpretation limits

- Repeated security-date observations and overlapping horizons are dependent; row counts are not independent sample sizes.
- Cross-sectional dependence, serial dependence, uncertainty intervals, and multiple testing were not analyzed.
- Changing PIT membership and early low-universe periods affect pooled and annual summaries.
- Missing endpoints and incomplete bars may be informative rather than random.
- The report does not identify the quarantined row or extreme return observations at SECID/date level.
- No target, label, feature, IC, feature-target association, model, walk-forward protocol, or portfolio metric has been selected or evaluated.

## Next stage: targeted diagnostic validation

The proposed checks are documented in `docs/research/eda/EDA_ANALYSIS.md`:
1. Characterize the 1,214 incomplete bars and clarify `bar_available` semantics.
2. Identify and trace the single quarantined mixed-scale observation.
3. Trace extreme future returns at each horizon to source rows and adjustment provenance.
4. Unit-test exact calendar endpoint mapping, return formulas, missing endpoints, and signal-date PIT cohort logic.
5. Characterize the 4,234 no-board rows, especially the 2006 and 2011 coverage gaps.

These checks are **proposed, not yet approved or implemented**. Do not change project code until the user approves their scope.

After validation, formulate a separate prediction-problem design from the evidence. It must decide whether prediction is justified, which outcomes/horizons warrant study, and whether one model, multiple models, or no model is appropriate. No feature/model implementation before explicit approval.

## Completed prior research

### Log returns

Daily log return `r_t = ln(P_t / P_{t-1})` is additive over consecutive periods and scale-normalized, but does not guarantee stationarity.

### Rolling Statistical Moments

**CLOSED on 2026-11-25.** The completed experiment covered rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240-session windows. Do not reopen, repeat its IC/correlation analysis, or add diagnostics without explicit user request or concrete new evidence. Closure does not imply automatic promotion of candidates.

## Binding research boundaries

- DS-first methods only; no trader-style indicators or disguised price-action heuristics.
- Preserve PIT membership, SECID identity, market-session timing, and missingness.
- Never forward-fill, create synthetic bars, bridge missing sessions, or automatically delete outliers.
- Do not repeat the already completed general structure/quality audit.
- `numtrades` is absent from the current EDA data contract.
- No feature engineering, IC, feature-target association, model fitting, walk-forward evaluation, or portfolio metrics during EDA and targeted validation.
- Portfolio metrics remain prohibited until a final model is approved; after approval, only the separately authorized decisive portfolio-level run is permitted.
- Repository inspection is not execution. Preserve provenance distinctions between user-run results, code inspection, and independent runtime validation.
