# Next Steps and Open Risks

Last updated: 2026-11-25

## Active project: ML direction prediction

Build and validate an ML model that predicts the direction of price movement for individual instruments.

Binding task definition:
- Dataset: daily OHLCV panel from historical point-in-time TOP50 Russian equities.
- Signal-date cohort: PIT TOP50 members on date t with a valid current bar.
- Prediction horizon: 5 trading sessions.
- Target: binary direction from adjusted Close[t] to adjusted Close[t+5]. Up=1, down=0; equal prices and unavailable endpoints are excluded.
- Features may use information available no later than the close of t.
- Final model WF protocol: expanding window, initial 3 years of training, monthly retraining, next month held out, and purge training observations whose 5-session target extends beyond the training cutoff.
- Statistical and predictive-model metrics on WF are permitted. Portfolio metrics are prohibited until final model approval. After approval, exactly one decisive portfolio-level run is allowed, with no tuning or iteration from its result.
- Research Agent researches and develops analytical capabilities; it does not make trading/allocation decisions.

## Completed stages

1. Log Returns: base representation documented.
2. Rolling Statistical Moments: **CLOSED on 2026-11-25**. The experiment covered 16 features (mean, variance, skewness, Fisher excess kurtosis over 20/60/120/240 sessions). The user explicitly directed that this family should not be revisited or repeatedly analyzed. Do not reopen without explicit user request or new concrete evidence.

## Next research proposal (not yet approved)

**Feature Research 03: OHLC price-formation decomposition.**

Study the structure of each daily bar:
- Overnight gap: ln(Open_t / Close_{t-1}).
- Intraday return: ln(Close_t / Open_t).
- High-low log range: ln(High_t / Low_t).
- Close location value: (2*Close_t - High_t - Low_t) / (High_t - Low_t), with explicit zero-range handling.
- Upper/lower wick proportions, after exact non-duplicative definitions are agreed.

Research question: does separating overnight repricing, intraday movement, and the close's position inside the day's range reveal distinct information about the t-to-t+5 direction target?

This is a researcher proposal, not an approved experiment. First teach the intuition and mathematics, inspect OHLC adjustment/data-quality constraints, agree exact formulas and hypotheses, then freeze the experiment specification before coding or viewing results. Do not assume these features are predictive.

## Research sequence

For each feature family:
1. Explain theory, intuition, mathematics, and interpretation.
2. State falsifiable hypotheses and identify plausible failure modes.
3. Agree formulas, edge-case handling, sample rules, and evaluation parameters before running.
4. Implement a reproducible isolated experiment only after specification approval.
5. Evaluate coverage, information content, temporal stability, redundancy, and uncertainty.
6. Record results and limitations; do not promote features automatically.
7. Propose the next capability gap / feature family.

Do not create broad indicator catalogs or jump prematurely to model fitting. Study interactions/conditional information later as a separate planned stage; standalone IC is not a complete feature-selection criterion.

## Evaluation firewall

- No portfolio-level metrics before explicit final-model approval.
- Do not inspect, calculate, report, compare, or use CAGR, Sharpe, MDD, returns, drawdowns, exposure, turnover, or portfolio application results during feature/model development.
- No separate fixed IS/VAL split; use the predeclared WF evaluation path.
- No repeated portfolio variants after approval. Exactly one decisive downstream portfolio evaluation.

## Data and operational constraints

- Internal historical MOEX market-data pipeline exists; no internal fundamental-data dataset or pipeline exists.
- Current external web information is not a point-in-time historical dataset. Any future external features require source, publication/retrieval timestamps, entity mapping, historical availability, and leakage controls.
- Preserve PIT membership, SECID identity, actual market-session timing, and missingness. No forward-fill or synthetic observations.
- Do not rebuild completed data stages without a concrete defect.
- Repository inspection is not local execution. Never claim tests or experiments ran unless actual execution output is available.
- Do not modify user-owned daily reports or project code without explicit authorization.
