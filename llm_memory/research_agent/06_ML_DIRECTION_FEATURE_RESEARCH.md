# ML Research: EDA and Prediction-Problem Design

Last updated: 2026-11-25

## Project objective

Use the PIT TOP50 MOEX daily market dataset to investigate whether the observed data supports a useful prediction problem. The final output is not assumed to be one model. The research may produce multiple tasks/models, a different analytical capability, or a conclusion that prediction is not justified.

Methodology is DS-first: statistics, probability, information theory, time-series analysis, statistical learning, uncertainty, heterogeneity, and nonstationarity. Do not use trader-style indicators or price-action heuristics as feature templates. Explicit exclusions include ATR, RSI, MACD, Bollinger Bands, stochastic oscillators, and candlestick patterns. OHLCV is the raw observation domain, not a mandate to construct trading signals.

## Current stage: descriptive EDA

Status: **approved; code committed to GitHub; user execution pending**.

Canonical specification: `docs/research/eda/EDA_SPEC.md`.

Implementation: `scripts/experiments/ml_1/eda/`.

The EDA describes:
- temporal panel coverage and PIT membership dynamics;
- distributions of adjusted OHLC, volume, value, value_60d, rank, and universe_size;
- annual and instrument-level heterogeneity;
- internal OHLC, price, volume/value, and bar-availability consistency;
- adjusted Close[t] to Close[t+1], Close[t+5], and Close[t+20] empirical behavior.

The three horizons are descriptive comparisons only. They do not define a target, label, model, or chosen forecast horizon. `numtrades` is absent from the current EDA data contract and is excluded.

No repeated general structure/quality audit. No feature engineering, IC, feature-target association, model fitting, walk-forward evaluation, or portfolio metrics during this EDA stage. No forward-fill, synthetic bars, outlier removal, or source-data mutation.

The user will pull the implementation, run it against local Parquet/SQLite data, and push the compact outputs to `docs/research/eda/`. Until then, code is committed but runtime results are not verified.

## Completed prior research

### Log returns

Daily log return representation:
`r_t = ln(P_t / P_{t-1})`.
It is additive over consecutive periods and scale-normalized, but does not guarantee stationarity. This is a statistical representation, not a proven predictor.

### Rolling Statistical Moments

Status: **CLOSED on 2026-11-25**. The completed experiment covered rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240-session windows. Do not reopen, repeat IC/correlation analysis, or propose additional diagnostics absent explicit user request or concrete new evidence. Closure does not imply automatic promotion of candidates into any future model.

## After EDA

Only after inspecting the actual EDA evidence, formulate the prediction problem from the data:
- decide whether prediction is justified at all;
- identify which outcome variables and horizons merit further study;
- determine whether the research needs one task/model, multiple tasks/models, or no model;
- define labels, sample eligibility, timestamp, baselines, leakage controls, validation and evaluation only after the empirical questions are clear.

Do not assume a binary up/down label, fixed 5-session horizon, fixed model family, or predeclared walk-forward protocol at this stage. No model implementation until the user approves a separate model-design plan.

## Research boundaries

- Research Agent produces validated analytical capabilities; it does not make trading/allocation decisions.
- No trader-style feature engineering or disguised technical indicators.
- No feature/model implementation without an approved research plan.
- Do not revisit closed work without explicit request or concrete new evidence.
- Keep PIT membership, SECID identity, market-session timing, and missingness intact.
- Never forward-fill missing prices or bridge missing sessions.
- Do not automatically delete extreme observations.
- Portfolio metrics are outside this EDA and prediction-design work. Any later change to evaluation scope requires explicit agreement.
- GitHub inspection is not execution. Runtime claims require actual user-supplied or authorized execution evidence.
