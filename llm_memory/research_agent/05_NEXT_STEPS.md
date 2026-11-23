# Next Steps and Open Questions

Last updated: 2026-11-23

## Current research state

The initial primitive discovery and diagnostic cycle has produced a compact runtime screener. Do not restart broad feature mining or repeat completed first-pass analyses without a specific unresolved question.

Current runtime information layer:
- Instrument state: drawdown_60, zscore_sma20_20, realized_vol_60.
- Separate market-state context: breadth_change_5 (primary) and breadth_sma20 (reference).
- Screener: scripts/tools/01_primitive_screener.py.
- Downstream specification: docs/tools/01_primitive_screener.md.

The breadth-based 100/75/50/25% exposure schedule is a user-proposed heuristic from a portfolio application test. It is not an approved statistically validated allocation model and is not implemented as a screener decision.

## Recommended next research: conditional downside-risk information in breadth regimes

### Research question

Do the four states defined by the level and five-session change of PIT TOP50 breadth contain stable, incremental information about the future downside-risk distribution of the market cohort, beyond recent cohort returns and the distribution of the three approved instrument-level primitives?

This is the most useful next step because existing breadth work has already examined mean/median forward returns, positive-return share, incremental return associations, and cross-sectional market structure. The remaining question most directly connected to the user's sizing hypothesis is whether breadth regimes distinguish future downside risk, not merely average forward return.

### Hypothesis

A weak or deteriorating breadth state may be associated with worse future downside outcomes or a fatter left tail. A rising breadth state may indicate improving participation, but the strength of that relationship may depend on whether breadth is already above or below 50%.

This is a hypothesis to test, not a conclusion.

### Predefined regime map

Use the user's existing thresholds and directions without optimization:

| Regime | Breadth level | Five-session change |
|---|---|---|
| A | >= 50% | > 0 |
| B | >= 50% | <= 0 |
| C | < 50% | > 0 |
| D | < 50% | <= 0 |

Do not search for a better threshold or tune the four exposure multipliers during this research.

### Outcomes to test

For fixed signal-date PIT TOP50 cohorts and horizons 5/10/20 sessions, examine:
- Equal-weight cohort forward return distribution, including lower quantiles.
- Share of constituents with negative forward returns.
- Cross-sectional downside tail measures, such as 10th-percentile return and expected shortfall of the worst decile, with coverage reported.
- Cohort downside semivariance / downside realized volatility over the forward window, using only observed valid outcomes.
- If adjusted OHLC history supports a clean definition, forward maximum adverse excursion from the next-session OPEN. Define the calculation before running it; do not mix close-to-close and open-to-low measures.

These are market-risk/state outcomes, not strategy returns or portfolio CAGR targets.

### Controls and inference

- Preserve PIT membership at signal date; do not require a security to remain in TOP50 during the outcome window.
- Keep SECID as the instrument identity. Never merge different SECIDs by issuer or ISIN.
- Use the same signal timing and forward outcome convention as existing research unless a separate, explicitly documented risk outcome requires another definition.
- Control for past cohort returns and cross-sectional medians of the three approved core primitives, matching the existing breadth incremental-analysis design where appropriate.
- Report regime counts, valid cohort coverage, and missingness for every horizon.
- Use HAC inference for suitable time-series mean comparisons and a block bootstrap for differences in tail/downside statistics. Account for overlapping forward horizons.
- Apply multiple-testing correction within clearly declared outcome/horizon families.
- Report full-sample results and established periods 2005–2012, 2013–2019, and 2020–2026. Do not interpret a sparse regime-period cell as evidence of no effect.
- Check sensitivity to extreme observations and coverage without deleting plausible market events.

### What would count as useful evidence

A regime difference should be directionally interpretable, have adequate coverage, survive dependence-aware uncertainty estimates, and show at least some consistency across periods. A result that exists only in one period or only for one arbitrarily chosen tail statistic should be treated as weak evidence.

A positive result would support breadth as a market-risk context for downstream allocation decisions. It would not validate the exact 100/75/50/25% multipliers. A negative or unstable result would weaken the case for relying on breadth as a downside-risk classifier, but would not invalidate its descriptive market-state role.

### Required preflight correction

Before running the experiment, reconcile the 50% boundary:
- User-approved rule: breadth_sma20 >= 0.50 is the upper-level regime.
- Current portfolio experiment code: breadth_level > 50.0 is the upper-level regime.
- Exactly 50% currently falls into the lower regime in code.

Confirm the intended inclusive boundary and make the experiment implementation match the approved specification before using its outputs. Do not change code until the user authorizes that implementation step.

## Secondary work after the downside-risk study

Only if the risk-state evidence is credible, run a narrowly scoped application sensitivity check:
- Keep the four regime definitions fixed.
- Compare the user's original heuristic with neutral/full exposure as a diagnostic.
- Do not optimize multipliers or threshold against MDD.
- Report exposure path, downside outcomes, missing-return treatment, turnover/cost assumptions, and drawdown as application diagnostics only.
- Keep this separate from the test of whether breadth contains information.

## Dataset and operational risks

- Verify the refresh script locally before relying on it.
- Resolve delayed publication after an empty MOEX response, calendar-yesterday cutoff, and missing SECID/board-pair onboarding.
- Do not rebuild completed historical-universe/raw/audit/adjustment stages without a concrete defect.
- Keep raw observations immutable and derived datasets rebuildable.
- Do not claim local execution or validation from GitHub code inspection alone.

## Research discipline

- No broad feature fishing.
- No linear regression as a primitive-discovery direction, no Hurst exponent, no sentiment layer, and no IMOEX until the user changes the scope.
- Do not optimize primitives for CAGR, Sharpe, MDD, or portfolio return.
- Distinguish information validation from a portfolio application experiment.
- The Research Agent recommends; the user approves scope changes and production promotion.
