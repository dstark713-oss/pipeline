# RC-002 — Changing Asset Dependence and Systemic Portfolio Risk

**Category:** Risk Control  
**Status:** approved for research; not empirically validated  
**Priority:** 2

## Hypothesis
Changes in the dependence structure among assets available at time (t) contain information about the concentration of portfolio risk over a subsequent horizon.

## Economic mechanism
During common macroeconomic or market-wide shocks, asset-specific drivers may become less important relative to shared exposures. Assets that appeared diversifying in calm periods may become more correlated during stress.

## Expected behavior and direction
An increase in common dependence is expected to reduce diversification benefits and increase the share of portfolio risk attributable to common movements. This concerns risk concentration, not asset returns.

## Economic-value mechanism
Detecting deterioration in diversification early enough may allow more robust allocation across assets and reduce simultaneous losses. The value is risk control, not standalone alpha.

## Instruments and horizons
Initial scope: MOEX TOP50 PIT constituents. Dependence windows: 20/60/120 sessions; portfolio-risk outcomes over 5/20/60 sessions. Broader asset classes are a later extension.

## Required data
Adjusted daily returns; PIT membership and synchronized observation coverage; historically valid instrument/sector classifications; predeclared portfolio weights or neutral test portfolios for measuring risk concentration.

## Candidate variables
Rolling pairwise Pearson and Spearman dependence summaries; median and distribution of pairwise correlations; share of negative/positive pairs; common-movement summaries and cross-sectional dispersion; stability under matched samples.

## Confounders
Changing universe size and membership, sector composition, missing observations, asynchronous trading, crisis outliers, and estimation noise in large correlation matrices.

## Applicability
Compare like-for-like samples or explicitly adjust for composition. Require minimum simultaneous coverage and uncertainty estimates. A failed strict complete-universe spectral calculation is not evidence that common movement is absent.

## Confirmation
- Dependence changes precede and explain changes in future portfolio-risk concentration beyond simple volatility estimates.
- Results persist across windows, subperiods, and matched universes.
- A predeclared diversification adjustment improves risk outcomes versus a comparable baseline without relying on unrealistic weights or costs.

## Rejection
- The signal is explained by changing membership or sample size.
- Dependence estimates are too unstable to be actionable.
- No incremental risk information remains after controlling for volatility and composition.
- Portfolio benefit disappears under realistic constraints or stress periods.

## EDA basis
EDA2 block 3 found positive but heterogeneous average pairwise dependence; block 4 found temporally dependent cross-sectional dispersion. The strict complete-universe spectral calculation had no eligible securities, so no spectral conclusion is available.
