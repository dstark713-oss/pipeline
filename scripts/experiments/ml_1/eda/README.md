# Descriptive EDA: PIT TOP50 Panel

This stage describes the data before any target or model is designed. It does not select a target, features, model family, or prediction horizon.

## Included analysis

1. Temporal panel coverage, annual membership counts, bar coverage, entrants/exits, and membership persistence.
2. Distributions of adjusted OHLC, volume, value, 60-session turnover value, PIT rank, and universe size. Market activity/price variables use `bar_available=1`; membership variables use all panel rows. Outliers are reported, never automatically removed.
3. Per-year distribution summaries and per-instrument coverage/activity summaries.
4. Internal consistency checks for OHLC constraints, positive adjusted prices, nonnegative volume/value, `bar_available`/close consistency, panel-close agreement with the board-selected adjusted history, and board/corporate-action composition.
5. Descriptive adjusted-close changes from t to t+1, t+5, and t+20 market sessions: absolute change, simple return, log return, distribution shape, positive/negative/zero shares, endpoint coverage, year and instrument breakdowns.

## Explicit exclusions

- No repeated general structure/quality audit; that stage was already completed.
- No `numtrades` analysis.
- No feature engineering, IC, feature-target association, model training, walk-forward evaluation, or portfolio metrics.
- No BUY/SELL labels or fixed model target. Horizons 1/5/20 are descriptive only.
- No forward-fill, synthetic bars, automatic outlier removal, or source-data mutation.

## Data handling

- Panel cohort is point-in-time TOP50 membership on date t.
- Current-price observations require `bar_available=1` and positive adjusted close.
- Future endpoints are taken from the adjusted SQLite history for the same SECID, not from future TOP50 membership. This avoids dropping an endpoint merely because the instrument later leaves TOP50.
- Horizon is counted on the TQBR/EQBR market-session calendar, excluding the already-defined market suspension interval.
- Board selection matches the panel pipeline: complete OHLC row first, then TQBR priority, EQBR fallback.
- No price is forward-filled. The horizon is counted on the full market calendar; only the observed start and exact t+h endpoint are required. Intermediate missing bars are never interpolated.
- SQLite is opened read-only.

## Run

From repository root:

```powershell
python scripts/experiments/ml_1/eda/run_eda.py
```

Dependencies: pandas, numpy, pyarrow. For Markdown table generation, pandas requires tabulate.

## Outputs

Generated under `docs/research/eda/`:

- `EDA_REPORT.md`
- `eda_metadata.json`
- `distribution_summary.csv`
- `distribution_by_year.csv`
- `instrument_coverage_summary.csv`
- `temporal_by_year.csv`
- `consistency_checks.csv`
- `consistency_categories.csv`
- `future_price_summary.csv`
- `future_price_by_year.csv`
- `future_price_by_secid.csv`

Generated outputs are compact aggregates, not raw row-level exports.
