# RC-003 — Unusual Trading Activity as a Possible Risk Warning

**Category:** Risk Control  
**Status:** approved for research; not empirically validated  
**Priority:** 3

## Hypothesis
Unusual trading activity relative to an instrument's own history contains incremental information about its future realized volatility or downside-tail risk, beyond information in current returns and volatility.

## Economic mechanism
An abrupt activity change may accompany new information, disagreement, repricing, or rapid position redistribution. These processes may precede larger price fluctuations, but high activity alone does not identify buying or selling pressure.

## Expected behavior and direction
The primary directional expectation is a positive association between unusual activity and future volatility/tail-risk measures. The sign and shape must be tested rather than assumed for every activity definition.

## Economic-value mechanism
If unusual activity provides an early warning of elevated risk, exposure can be adjusted before adverse movements occur. This is a risk-control mechanism, not a directional trading signal.

## Instruments and horizons
Initial scope: MOEX TOP50 PIT constituents. Outcomes: 1/5/20 sessions, with 5/20 as primary candidate horizons. Minute data and other markets are outside the initial scope.

## Required data
Daily traded value (Value), volume, adjusted returns; PIT membership, valid-bar availability, and trading calendar; historical instrument-specific activity distributions. A later extension may use transaction-level or order-book data with reliable aggressor-side information.

## Candidate variables
Log Value relative to the instrument's rolling historical median; robust standardized activity surprise; change in Value and its persistence; Value concentration context; Volume only with explicit instrument-scale normalization.

## Confounders
Instrument size, liquidity, current return, current volatility, corporate events, market-wide activity, calendar effects, universe changes, and reporting/board aggregation differences.

## Applicability
Prefer Value over raw Volume for cross-instrument economic comparison. Normalize activity within each instrument and use only values available at the signal timestamp. Daily OHLCV cannot reconstruct true order flow or aggressor direction; number of trades is not order flow.

## Confirmation
- Activity surprise adds out-of-sample information about future volatility or downside tails beyond current return and volatility.
- Effect is stable across periods and instrument groups.
- A predeclared exposure adjustment improves a risk objective after costs and opportunity cost.

## Rejection
- Incremental effect vanishes after controls for size, liquidity, current return, and volatility.
- Effect is isolated to a few events or instruments.
- Activity does not precede the risk outcome.
- Economic benefit is not robust to costs and baseline choice.

## EDA basis
EDA2 block 7 found highly concentrated activity and differences in same-day return distributions across activity groups. Those same-day conditional distributions do not establish future risk prediction.
