# DM-002 — Trading Activity and Future Relative Returns

**Category:** Direct Monetization  
**Status:** approved for research; not empirically validated  
**Priority:** 2

## Hypothesis
Unusual trading activity relative to an instrument's own history contains information about its future relative return that is incremental to past relative returns, current volatility, and instrument size/liquidity.

## Economic mechanism
Activity changes may reflect new information, changing investor attention, disagreement, or capital reallocation. If prices adjust gradually, activity may precede subsequent relative repricing. High activity can also accompany exhaustion or forced liquidation, so the sign is not assumed.

## Expected behavior and direction
The direction is deliberately unresolved at registration. Competing alternatives:
- positive: unusual activity accompanies information incorporated gradually;
- negative: unusual activity marks temporary overextension, liquidation, or a short-lived demand shock.

The primary test must define a two-sided association or predeclare a directional mechanism before seeing outcomes.

## Economic-value mechanism
Use activity information to improve cross-sectional ranking and selection of instruments with higher expected future relative returns. Direct monetization requires incremental net value over a baseline that already uses past returns and risk information.

## Instruments and horizons
Initial scope: MOEX TOP50 PIT constituents. Candidate horizons: 5/20/60 sessions. Daily data first; minute/trade/order-book data is a later, separately approved extension.

## Required data
Daily Value and Volume; adjusted returns and PIT membership; historical activity for within-instrument normalization; liquidity and transaction-cost estimates; sector and market controls where reliable.

## Candidate variables
Robust activity surprise relative to rolling own-history median/MAD; relative Value rank within PIT universe; change and persistence of activity surprise; predeclared interactions with past relative return and volatility.

## Confounders
Size, liquidity, current return, volatility, sector news, corporate events, broad market activity, calendar effects, and changing universe composition.

## Applicability
Use Value as the primary economic activity measure; raw Volume is not comparable across instruments without normalization. Daily OHLCV does not reveal trade aggressor side or true order flow. Number of trades is not a substitute for order-flow direction.

## Confirmation
- Activity adds out-of-sample relative-return information beyond baseline variables.
- Direction and timing are interpretable and reasonably stable across periods.
- A predeclared ranking/selection implementation produces positive net value after costs, slippage, turnover, and liquidity constraints.

## Rejection
- Incremental information disappears after controls.
- Direction changes unpredictably across periods.
- Results depend on post-hoc activity thresholds or one small group.
- Net economic value is erased by turnover and execution costs.

## EDA basis
EDA2 block 7 established activity concentration and same-day conditional return differences only. It did not test future returns. This is a mechanism-driven extension, not an EDA-proven effect.
