# EDA Analysis: PIT TOP50 Panel

**Reviewed:** 2026-11-26  
**Generated run:** 2026-11-25 18:51:06 UTC  
**Code revision:** `46fb41a8a289609313c06defce2ec3f72c1e500e`  
**Source report:** `docs/research/eda/EDA_REPORT.md`

## Executive assessment

The EDA run completed against the user's local Parquet panel and adjusted SQLite database. The panel has broad historical coverage, but its cross-sectional depth and bar availability vary materially over time. Adjusted-close endpoint coverage is high at all three descriptive horizons. The pooled return distributions are heavy-tailed and change substantially by year.

The evidence is sufficient to move from broad description to a narrow diagnostic-validation stage. It is **not** sufficient to select a prediction target, forecast horizon, feature family, or model. No statistical inference, feature-target association, or predictive evaluation was performed.

## 1. Dataset coverage and temporal composition

- 203,403 PIT membership rows, 214 distinct SECIDs, 5,490 panel dates.
- Panel date range: 2005-01-11 to 2026-11-25.
- Full TQBR/EQBR market calendar: 5,740 sessions.
- 199,169 rows have `bar_available=1`, giving 97.918% overall bar coverage; 4,234 membership rows (2.082%) have no selected board bar.
- Median daily bar coverage is 100%; the 5th percentile is 81.82%. Mean daily membership is 37.05, while the median universe size is 50.

The universe is not cross-sectionally comparable across the full history without accounting for composition. Average daily membership was about 10-17 in 2005-2009, 21 in 2010, 30 in 2011, and reached 50 from 2015 onward. Coverage also varies: 2006 is 83.52%, and 2011 is notably low at 76.91%; most recent years are near 99-100%.

**Implication:** early-period estimates will have a smaller and different eligible cross-section. Any later time-series comparison must report both date coverage and cross-sectional sample size, and must not treat the panel as a constant 50-stock universe from 2005.

## 2. Observed-variable distributions

Pooled adjusted price levels are extremely right-skewed: adjusted Close has median 120.68, 95th percentile 3,949.15, 99th percentile 9,146.38, skewness 17.74, and excess kurtosis 408.86. Volume is even more skewed (skewness 87.20; excess kurtosis 10,755), while Value has skewness 10.61 and excess kurtosis 326.73. `value_60d` is also strongly right-skewed (median about 20.45bn; 95th percentile about 335.6bn).

These pooled level moments combine different securities, price scales, activity scales, and historical periods. They are useful as distribution diagnostics, but they are not meaningful evidence that a pooled raw level is a suitable model input. The extreme skewness/kurtosis is not, by itself, proof of corrupted observations.

No winsorization, trimming, or automatic outlier removal is justified by this EDA. Any later transformation must be motivated by a defined estimand and checked by instrument/time cohort.

## 3. Internal consistency and provenance

The consistency checks are strong on rows with complete OHLC:

- 197,955 complete OHLC observations satisfy all checked price-order constraints.
- No non-positive adjusted OHLC prices were found among the corresponding non-missing values.
- No negative Volume or Value was found among the 199,169 rows flagged as bar-available.
- Panel adjusted Close matches the board-selected adjusted SQLite history on all 197,955 rows where both values are present, at the stated tolerance of 1e-8.

There is one important unresolved data-contract issue:

- 1,214 of 199,169 `bar_available=1` rows (0.610%) have incomplete OHLC.
- Separate checks also report 1,214 `bar_available=1` rows with missing adjusted Close and 1,214 with missing selected adjusted-history Close. The aggregate report does not provide a row-level cross-tab proving these are exactly the same observations.

This may mean `bar_available` denotes the existence of a source/board row rather than the availability of a usable adjusted OHLC bar. The report does not establish the cause. The flag's semantics should be verified before it is used as a general eligibility condition.

Composition diagnostics show TQBR selected for 81.56% of available rows and EQBR for 18.44%. 1,218 rows have both boards represented; 4,234 have no board row. One row is classified `QUARANTINED_MIXED_SCALE`. The dataset pipeline context documents one quarantined corporate-action observation (BELU effective-date event), but the aggregate EDA output does not identify the SECID/date, so that association must be checked rather than assumed.

## 4. Future adjusted-close behavior

The cohort consists of PIT TOP50 members at signal date t with `bar_available=1` and positive adjusted Close at t. Future endpoints are exact t+h positions on the full market-session calendar. A security is not required to remain in TOP50 at t+h. Intermediate bars are not interpolated.

| Horizon | Valid endpoints | Endpoint coverage | Mean simple return | Median simple return | Std. simple return | Mean log return | Positive / negative / zero |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +1 session | 197,325 | 99.682% | +0.027% | -0.025% | 2.637% | -0.0066% | 48.12% / 50.47% / 1.41% |
| +5 sessions | 196,779 | 99.406% | +0.125% | 0.000% | 5.961% | -0.0481% | 49.46% / 49.99% / 0.55% |
| +20 sessions | 195,132 | 98.574% | +0.521% | +0.095% | 11.757% | -0.1651% | 50.43% / 49.34% / 0.23% |

The start cohort contains 197,955 observations. Endpoint unavailability increases with horizon (630, 1,176, and 2,823 respectively), but remains below 1.5% at +20.

The arithmetic and logarithmic means differ, especially at +20. The simple-return distributions have substantial positive skew, while the log-return distributions show strong tail weight and negative skew at +5/+20. For example, +20 simple-return skewness is 1.09 with excess kurtosis 15.38; +20 log-return skewness is -1.20 with excess kurtosis 20.25. The +20 simple-return maximum is +330.3%, while the minimum is -93.35%. These extremes should be traced to source observations before any later modeling decision; they must not be deleted just because they are large.

Annual cohort summaries vary substantially. Examples for mean +20 log return include approximately -11.19% in 2008, -4.00% in 2022, -2.13% in 2024, and -3.18% in 2026, versus +6.74% in 2009, +3.02% in 2016, and +3.04% in 2023. This is descriptive evidence of time variation, not a significance test or proof of a forecastable regime. Cohort composition and overlapping observations also change across years.

**Interpretation:** the unconditional direction shares are close to balanced. The EDA does not establish a stable directional edge. The positive arithmetic means do not contradict near-balanced direction shares, because return magnitudes are asymmetric and heavy-tailed.

## 5. Limitations

- Observations are repeated across securities and dates; securities can appear in many overlapping horizons. The reported rows are not independent samples.
- Cross-sectional dependence and serial dependence have not been modeled.
- The PIT universe changes over time, and early years have fewer constituents.
- Missing endpoints and incomplete current bars may be informative rather than random.
- The aggregate report does not identify the SECID/date of the quarantined mixed-scale row or the most extreme future-return observations.
- No confidence intervals, hypothesis tests, multiple-testing corrections, IC, feature-target association, model fitting, walk-forward evaluation, or portfolio metrics were computed.

## 6. Proposed targeted validation before prediction-problem design

This is a proposal for the next stage, not an authorization to implement. Agree the checks before code changes.

1. **Clarify `bar_available` semantics and the 1,214 incomplete rows.** Produce compact counts by year, SECID, selected board, and missing OHLC field; inspect a small traceable sample against the adjusted SQLite rows. Decide whether the flag means source-row existence or usable-bar completeness. Do not mutate the source data.
2. **Trace the single quarantined mixed-scale row.** Identify SECID/date, board composition, adjustment event/status, and corresponding raw/adjusted source values. Confirm whether it is the already documented BELU event.
3. **Trace extreme future returns.** For each horizon, identify a small set of minimum/maximum simple and log-return observations with SECID, signal date, endpoint date, current/future adjusted Close, and source adjustment status. Determine whether they are legitimate market/corporate-action outcomes or data anomalies. Do not remove them automatically.
4. **Test endpoint and return calculations.** Unit tests should verify exact calendar offsets for +1/+5/+20, simple/log return formulas, missing endpoint behavior, and the rule that future membership in TOP50 is not required. Intermediate missing bars must not be interpolated.
5. **Characterize missing-bar coverage.** Explain the 4,234 rows with no board bar, with special attention to 2006 and 2011, and distinguish no source observation from other known exclusions or data availability boundaries.

No generic structure/quality audit should be repeated. No feature engineering, IC, target selection, model fitting, or portfolio evaluation is part of these checks.

## Current decision

EDA is **reviewed; descriptive stage is ready for targeted validation**. Prediction-problem design remains blocked until the user approves and the agreed diagnostics are completed. No target, label, model, or forecast horizon is selected.
