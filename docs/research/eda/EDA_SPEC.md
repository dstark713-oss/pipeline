# EDA Specification: PIT TOP50 Panel

Status: approved scope; implementation committed; runtime results pending user execution.

## Objective

Describe the observed panel and the empirical behavior of adjusted closing prices before choosing any prediction target, feature set, model family, or prediction horizon. EDA is allowed to conclude that no useful prediction task is supported.

## Included scope

1. **Temporal structure and coverage**
   - Annual panel membership counts, distinct SECIDs, available bars and daily cross-sectional coverage.
   - Daily membership entrants/exits and membership persistence.
   - Instrument-level membership coverage and activity summaries.

2. **Observed-variable distributions**
   - Adjusted OHLC, volume, value.
   - `value_60d`, PIT rank, universe size.
   - Center, dispersion, quantiles, skewness, excess kurtosis, and extreme values.
   - Overall and by-year summaries; instrument-level coverage/activity summaries.
   - Market price/activity variables use rows with `bar_available=1`; membership variables use all PIT membership rows.
   - No automatic outlier deletion or winsorization.

3. **Internal consistency diagnostics**
   - OHLC constraints and positive adjusted prices.
   - Nonnegative volume and value.
   - `bar_available` consistency with adjusted Close.
   - Diagnostics only: no automatic data correction.

4. **Future adjusted-close behavior**
   - Compare adjusted Close at t with adjusted Close at t+1, t+5, and t+20 market sessions.
   - Report absolute price change, simple return, and log return.
   - Report distribution shape and positive/negative/zero shares.
   - Report endpoint availability, annual variation, and per-instrument variation.
   - Cohort is PIT TOP50 membership at t with `bar_available=1` and positive current adjusted Close.
   - Future endpoint is taken from the same SECID's adjusted history, regardless of whether it remains in TOP50 at t+h.

## Exclusions

- General structure/quality audit already completed earlier; do not repeat it.
- `numtrades` is absent from the current EDA data contract and is not analyzed.
- No feature engineering, feature-target association, IC, model fitting, walk-forward evaluation, or portfolio metrics.
- Horizons 1/5/20 are descriptive comparison points, not a selected prediction target or model specification.
- No assumption that the eventual system must be a single model or even that a predictive model is warranted.

## Data handling

- Panel: `data/processed/top50/top50_panel.parquet`.
- Adjusted history: `data/processed/moex_daily_adjusted.sqlite`, opened read-only.
- Market-session calendar: distinct TQBR/EQBR dates, excluding 2022-02-28 through 2022-03-23.
- Price selection: complete OHLC row first, then TQBR priority, EQBR fallback.
- No forward-fill, synthetic bars, or source-data mutation. Horizons use exact calendar endpoints; intermediate missing bars are not interpolated.
- No raw row-level exports. Save only compact aggregate outputs.

## Implementation

- Code: `scripts/experiments/ml_1/eda/`.
- Run: `python scripts/experiments/ml_1/eda/run_eda.py` from repository root.
- Output: this directory, `docs/research/eda/`.
- Dependencies: pandas, numpy, pyarrow, tabulate.

## Acceptance / interpretation rules

- Clearly report sample counts and endpoint coverage for each horizon.
- Keep absolute price changes separate from scale-relative returns; absolute changes are not cross-instrument comparable.
- Separate unavailable endpoints from observed zero returns.
- Preserve PIT membership and SECID identity.
- Do not interpret descriptive positive-return shares as forecasts.
- Runtime success and findings remain unverified until the user runs the code and pushes the generated report.
