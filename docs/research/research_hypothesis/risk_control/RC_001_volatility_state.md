# RC-001 — Volatility-State Forecasting for Exposure Adaptation

**Category:** Risk Control  
**Status:** approved for research; not empirically validated  
**Priority:** 1

## Hypothesis
Information available at time (t) about the recent scale and dynamics of an instrument's returns improves estimates of its realized volatility over the next 5, 20, and 60 trading sessions relative to a fixed historical estimate.

## Economic mechanism
Information arrival, uncertainty, repricing, and position adjustment are not uniform through time. Volatility can cluster because shocks and uncertainty persist rather than disappearing immediately.

## Expected behavior and direction
Higher recent realized volatility is expected to be associated with higher future realized volatility. The relationship may be nonlinear and may vary by instrument and market state.

## Economic-value mechanism
If future risk can be estimated usefully, capital exposure can be adjusted before risk is fully realized. The intended value is lower loss severity and improved risk-adjusted capital use, not directional alpha. A simple reduction in invested capital is insufficient: account for missed returns, cash yield, turnover, costs, and comparable risk/exposure baselines.

## Instruments and horizons
Initial scope: PIT constituents of the MOEX TOP50 panel. Horizons: 5, 20, and 60 market sessions. Other asset classes require separate validation.

## Required data
Adjusted daily prices/returns; valid-bar availability and exchange calendar; PIT membership and instrument identity. Cash-return assumptions are needed only for a later economic simulation and must not be mistaken for historical realized cash returns.

## Candidate variables
Rolling standard deviation and unscaled MAD over 20/60/120/240 sessions; recent change in scale estimates; relative scale versus the instrument's own past distribution; lagged absolute and squared returns. These are candidates, not a frozen feature set.

## Confounders
Market-wide shocks, individual events, changing universe membership, unequal history length, missing bars, extreme observations, structural breaks, and liquidity changes.

## Applicability
Use only information available at the decision timestamp. Require sufficient valid observations, preserve missingness, and evaluate across multiple periods and instruments. Control for common market-wide risk where appropriate.

## Confirmation
- Future realized-volatility estimates are better calibrated or more accurate than predeclared simple baselines.
- Incremental information persists across periods and instrument groups.
- Results are not driven by a few crisis episodes or securities.
- An exposure rule designed after validation improves a predeclared economic objective after costs and opportunity cost, relative to a meaningful baseline.

## Rejection
- No incremental forecast value over simple historical baselines.
- The effect disappears after controlling for common market risk or sample composition.
- Performance is concentrated in one regime or a few instruments.
- Any apparent portfolio benefit is explained solely by holding less capital or unrealistic cash/cost assumptions.

## EDA basis
EDA2 blocks 1, 2, 4, and 5 found heavy-tailed returns, stronger temporal dependence in absolute/squared returns than signed returns, temporal dependence in cross-sectional dispersion, and time-varying scale within securities. These are descriptive motivations, not proof of future volatility predictability.
