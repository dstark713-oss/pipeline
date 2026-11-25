# EDA v2: Statistical Structure and Behaviour of the PIT TOP50 Panel

Status: proposed research plan; implementation not approved or started.  
Date: 2026-11-26

## Purpose

The first EDA pass mainly described schema coverage, marginal source-variable distributions, consistency checks, and pooled future-price summaries. That is not sufficient to characterize the statistical behaviour of the PIT TOP50 panel or to generate defensible research hypotheses.

EDA v2 is a data-characterization study. It asks how returns and activity are distributed, how observations depend on time and on other securities, how the cross-section changes, and whether stable heterogeneity or conditional structure is visible. It does not assume that a predictive model must be built.

## Scope boundaries

- Use the existing adjusted daily panel and its PIT membership/calendar semantics.
- Do not repeat the completed general data-quality audit.
- The known 1,214 incomplete bars are a refresh-pipeline issue. Repair them through the separate candle overlay utility; do not make EDA v2 a source-cleaning project.
- Do not spend a separate analysis cycle on the single BELU quarantined row.
- Missing bars and changing universe coverage may be described only where needed to understand sample composition or potential selection bias.
- No trader indicators, technical signals, candlestick patterns, or price-action heuristics.
- No feature selection, IC leaderboard, model fitting, walk-forward validation, trading rules, or portfolio metrics.
- Descriptive conditional distributions may be examined to formulate hypotheses, but they must not be presented as predictive evidence.

## Research questions and analyses

### 1. Return distribution geometry

**Question:** What does the distribution of daily security-level log returns look like, and how does its shape vary across instruments and time?

Analyses:
- Daily log returns from consecutive valid adjusted closes, with no bridging across missing sessions.
- Pooled and per-security distributions: mean, median, standard deviation, MAD, quantiles, skewness, excess kurtosis, and tail exceedance frequencies.
- Tail-focused quantiles (for example 1%, 5%, 95%, 99%) and empirical left/right tail asymmetry.
- Annual and rolling-period summaries to expose temporal changes.
- Compare pooled, equal-security-weighted, and date-level cross-sectional summaries so large/long-lived constituents do not silently dominate.

Hypotheses this can motivate: heavy-tail persistence, instrument-specific distribution families, time-varying asymmetry, and non-constant scale.

### 2. Temporal dependence

**Question:** Are returns independent through time, and does dependence differ between signed returns and measures of return magnitude?

Analyses:
- Per-security ACF at lags 1, 2, 5, 10, and 20 for returns, absolute returns, and squared returns.
- Ljung-Box tests per security for predeclared lag sets, with minimum effective sample requirements and Benjamini-Hochberg correction across securities.
- Summarize the distribution of test statistics/effect sizes, not only counts of small p-values.
- Repeat on broad time segments only where sample size permits.
- Keep missing sessions missing; never create artificial zero returns.

Interpretation:
- Dependence in signed returns and dependence in magnitudes are different questions.
- Significant absolute/squared-return dependence is evidence of volatility clustering, not by itself a volatility forecast or a model recommendation.
- Overlapping windows and repeated tests must be handled explicitly.

### 3. Cross-sectional dependence and common movement

**Question:** How strongly do securities co-move, and is that structure stable?

Analyses:
- Pairwise Pearson and Spearman correlations of aligned daily log returns.
- Distribution of pairwise correlations by year and broad time segment.
- Rolling cross-sectional correlation summaries for 60/120/240-session windows.
- Correlation-matrix eigenvalue spectrum and variance concentration as descriptive linear-algebra diagnostics.
- PCA may be used strictly as an exploratory decomposition of contemporaneous return covariance, not as a fitted prediction model. Report stability and sensitivity to universe composition.

Hypotheses this can motivate: common market component, changing dependence regimes, clusters of co-moving securities, and residual idiosyncratic variation.

### 4. Cross-sectional dispersion and breadth as statistical summaries

**Question:** How dispersed are security returns within each market session, and how persistent is that dispersion?

For each date:
- Cross-sectional mean, median, standard deviation, MAD, IQR, and selected quantiles of returns.
- Fraction of securities with positive, negative, and zero returns.
- Number of valid securities contributing to each statistic.
- Time-series distributions and autocorrelation of those date-level statistics.
- Annual/rolling summaries and comparison across universe-size strata.

These are descriptive cross-sectional statistics, not trading breadth signals or allocation rules.

### 5. Heterogeneity of scale and volatility

**Question:** Are return scale and distribution shape stable across securities, or are there persistent groups?

Analyses:
- Per-security standard deviation, MAD, quantile range, skewness, and tail measures.
- Rolling dispersion measures over 20/60/120/240 sessions, used only to describe changing variance.
- Compare within-security temporal variation with between-security variation.
- Robust group comparisons (for example Brown-Forsythe/Levene where assumptions and sample construction are suitable); report effect sizes and uncertainty.
- Avoid treating each security-day as independent.

Hypotheses this can motivate: stable scale heterogeneity, time-varying volatility, and changes in relative dispersion.

### 6. PIT membership dynamics and rank mobility

**Question:** How stable is the research population, and how quickly do securities move through the TOP50 ranking?

Analyses:
- Membership tenure distributions, entry/exit rates, and consecutive membership persistence.
- Rank transition matrices and rank changes for securities present on adjacent dates.
- Rank autocorrelation/persistence by lag.
- Universe-size and cohort summaries by period.
- Separate actual rank mobility from membership turnover.

This extends the first EDA pass's annual counts into a statistical description of population dynamics.

### 7. Activity, concentration, and conditional structure

**Question:** How is market activity distributed across the cross-section, and does return behaviour differ descriptively across activity/rank strata?

Analyses:
- Cross-sectional distributions of Volume, Value, and value_60d.
- Per-date concentration measures (for example top-5/top-10 share and Herfindahl concentration) using only valid positive activity observations.
- PIT rank and activity strata defined on date t; compare contemporaneous return distributions and, as a separate explicitly descriptive view, the previously specified +1/+5/+20 return distributions.
- Report group sizes, medians, quantiles, dispersion, and uncertainty. Do not rank strata by predictive performance or compute an IC leaderboard.

This is exploratory stratification for hypothesis generation, not feature approval or evidence of deployable prediction.

## Statistical inference protocol

- Define the estimand and sample unit for every test.
- Preserve time ordering, PIT membership, and security identity.
- Do not pool dependent security-day observations and then use iid standard errors.
- Where uncertainty is estimated, use date-block or other dependence-aware resampling appropriate to the statistic; explain what dependence is preserved.
- Correct families of repeated per-security/per-lag tests for multiplicity (BH where suitable).
- Report effect sizes, confidence intervals, sample sizes, and test diagnostics together. P-values alone are not conclusions.
- Distinguish statistical significance from economic or predictive usefulness.
- Predeclare thresholds, minimum sample sizes, lag sets, and comparison groups before running tests.

## Proposed deliverables

1. EDA_V2_REPORT.md: research questions, methods, results, figures/tables summarized in text, interpretations, caveats, and hypotheses.
2. Compact CSV aggregates for per-security, per-year, per-date, and pairwise summaries where useful. No raw daily exports or giant correlation matrices in GitHub.
3. Statistical test summary with test family, sample size, statistic, effect size, p-value, adjusted p-value, and interpretation.
4. A final hypothesis register: supported descriptively / not supported / inconclusive, evidence, confounders, and what would be required to test further.

## Proposed execution order

1. Return distribution geometry.
2. Temporal dependence.
3. Cross-sectional dependence/common movement.
4. Date-level dispersion and breadth statistics.
5. Instrument heterogeneity.
6. PIT membership/rank mobility.
7. Activity concentration and conditional stratification.

The order can be revised after the first result review, but no implementation begins until the user approves the plan and the output contract.
