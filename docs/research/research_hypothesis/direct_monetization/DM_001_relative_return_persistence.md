# DM-001 — Relative-Return Persistence Across Instruments

**Category:** Direct Monetization  
**Status:** approved for research; not empirically validated  
**Priority:** 1

## Hypothesis
Relative performance of an instrument versus the contemporaneous eligible universe over a past formation window contains information about its future relative return over a subsequent holding horizon.

## Economic mechanism
Information about businesses, sectors, and market conditions may be incorporated into prices at different speeds. Investor attention, heterogeneous expectations, and gradual portfolio adjustment can produce delayed relative repricing. This is a candidate explanation, not an established fact.

## Expected behavior and direction
The initial hypothesis is positive persistence: instruments with higher past relative returns are expected to have higher subsequent relative returns. The effect may decay with horizon and vary by regime. Reversal is a competing alternative that must be reported, not hidden.

## Economic-value mechanism
Rank eligible instruments using information available at formation time and allocate capital toward instruments with higher estimated future relative returns. Monetization requires positive net performance after costs and constraints.

## Instruments and horizons
Initial scope: MOEX TOP50 PIT constituents. Candidate formation windows: 20/60/120/240 sessions. Candidate future horizons: 5/20/60 sessions. Stage 06 must predeclare primary comparisons and multiple-testing families.

## Required data
Adjusted daily prices/returns; PIT universe membership and ranks; trading calendar and bar availability; historically valid sector classifications if available; transaction costs, liquidity, and execution assumptions for later economic validation.

## Candidate variables
Past cumulative log return relative to the universe; cross-sectional percentile/rank of past return; relative-return differences across formation windows; historical rank persistence and changes; sector-relative return only if reliable PIT sector data exists.

## Confounders
Market beta, sector composition, size, liquidity, volatility, price limits, corporate events, survivorship/selection bias, membership exits, and overlapping formation/holding periods.

## Applicability
All ranks and returns must use the point-in-time eligible universe. Future membership must not determine historical eligibility. Define treatment of exits, new entrants, and unavailable future prices before testing.

## Confirmation
- Positive future relative-return association survives temporal out-of-sample validation.
- Effect is not explained by market/sector exposure or simple risk differences.
- Results persist across subperiods and reasonable predeclared horizons.
- An implementable ranking portfolio has positive net value versus predeclared benchmarks after costs, liquidity limits, and turnover.

## Rejection
- No reproducible future relative-return information.
- Apparent effect is driven by survivorship, PIT membership errors, or one market regime.
- Net value disappears after realistic costs or capacity constraints.
- Results require post-hoc window selection.

## EDA basis and origin
EDA2 provides descriptive context on return heterogeneity, dependence, rolling scale, and PIT membership. It did not test cross-sectional future relative-return persistence. This is a mechanism-driven hypothesis and a new predictive claim.
