# DM-004 — Compensation for Bearing Risk

**Category:** Direct Monetization  
**Status:** approved for research; not empirically validated  
**Priority:** 4

## Hypothesis
Risk characteristics observable at portfolio-formation time are associated with systematic differences in subsequent relative returns across instruments, after controlling for known exposures and confounders.

## Economic mechanism
Investors may demand compensation for bearing risks that are difficult to diversify or hedge. Conversely, behavioral preferences, constraints, or lottery-like demand may cause some high-risk assets to deliver lower subsequent returns. Both are plausible competing mechanisms.

## Expected behavior and direction
The sign is not fixed at registration:
- positive premium: greater exposure to a priced risk is compensated by higher future expected return;
- negative premium: certain risk characteristics are associated with lower future return.

The research must identify which risk dimension is economically meaningful rather than treating total volatility as a universal risk measure.

## Economic-value mechanism
Estimate return compensation associated with distinct risk exposures and use it to avoid assets with unattractive expected-return-to-risk trade-offs or select assets with positive net expected compensation.

## Instruments and horizons
Initial scope: MOEX TOP50 PIT constituents. Candidate horizons: 20/60/120 sessions; risk-estimation windows: 20/60/120/240 sessions.

## Required data
Adjusted daily returns and PIT membership; market and sector exposures; liquidity/size controls; risk estimates available at formation time; transaction-cost assumptions for later economic validation.

## Candidate variables
Total and downside volatility; market-related and residual risk, if estimable without lookahead; tail measures and cross-sectional risk ranks; predeclared interactions with liquidity and market state.

## Confounders
Market beta, sector effects, size, liquidity, leverage, survivorship, changing membership, nonstationarity, and measurement error in risk estimates.

## Applicability
Separate compensated systematic risk from diversifiable idiosyncratic volatility. Ensure all risk estimates use only past observations and have sufficient history. Do not assume higher total volatility must command higher returns.

## Confirmation
- A stable conditional relation exists between a clearly defined risk exposure and future relative returns.
- The relation survives controls, temporal validation, and alternative risk measures.
- Economic interpretation distinguishes compensation from behavioral mispricing.
- Any implementable selection approach has positive net value after costs and realistic constraints.

## Rejection
- No stable relation or sign reversals cannot be explained by predeclared regimes.
- Apparent premium is explained by market beta, sector, size, or liquidity.
- Effect fails out-of-sample or is too small after costs.
- The risk measure is not reliably observable at formation time.

## EDA basis
EDA2 blocks 1 and 5 documented heavy tails and time-varying scale. They did not test risk premia. This is primarily mechanism-driven and requires an explicit theoretical definition of priced risk in Stage 06.
