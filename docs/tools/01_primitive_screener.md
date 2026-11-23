# 01_primitive_screener: Instrument State Snapshot

Last updated: 2026-11-23

## Purpose

The Primitive Screener produces a current descriptive snapshot of the 50 instruments in the latest point-in-time (PIT) TOP50 panel.

It exposes three approved instrument-level primitives:

- `drawdown_60`
- `zscore_sma20_20`
- `realized_vol_60`

This is an information layer for a downstream agent. It is not a trading strategy, trade signal generator, portfolio optimizer, position-sizing module, or automatic execution system.

The screener does not produce a combined score or an instruction to buy, sell, hold, increase, or reduce a position. The downstream agent is responsible for interpreting the information in the context of its own portfolio, mandate, risk limits, and other available information.

## Implementation

Script:

`scripts/tools/01_primitive_screener.py`

Run from the repository root:

```powershell
python scripts/tools/01_primitive_screener.py
```

Run with interactive ticker inspection:

```powershell
python scripts/tools/01_primitive_screener.py --inspect
```

With `--inspect`, the tool prompts for one or more SECIDs separated by spaces:

```text
SBER DOMRF
```

Input is normalized to uppercase. The inspection command reports only instruments in the latest PIT TOP50 snapshot. A ticker outside the current panel is reported as not present; the tool does not silently expand the universe.

## Inputs

- `data/processed/top50/top50_panel.parquet`
- `data/interim/primitive_research/primitive_features.parquet`

The panel defines the current PIT TOP50 cohort and its liquidity rank. The feature frame supplies primitive values calculated on the same signal date.

The screener selects the maximum `tradedate` in the panel, then left-joins feature values by `SECID` for that exact date. It retains every row in the panel, including a member without an actual bar on the snapshot date.

The feature frame must be current through the selected panel date. If it is stale, the screener stops and instructs the operator to rebuild it:

```powershell
python scripts/experiments/primitives/05_build_primitive_features.py
```

## Output

The tool writes one CSV:

`data/interim/screener/latest_primitive_snapshot.csv`

The CSV is a wide snapshot with one row per current PIT TOP50 member. It contains:

- `snapshot_date`: panel date used for the snapshot.
- `secid`: MOEX instrument identifier.
- `panel_rank`: PIT TOP50 liquidity rank, not a primitive rank.
- `bar_available`: whether the panel has an actual bar for the instrument on the snapshot date.
- `instrument_status`: `OK`, `NO_BAR`, or `FEATURES_INCOMPLETE`.
- `missing_primitives`: primitive columns with no valid value.
- Each primitive value, its cross-sectional rank, and its percentile among valid current-panel observations.

The CSV is written atomically and encoded as UTF-8 with BOM for spreadsheet compatibility. It is a local runtime artifact and must not be committed to Git.

## Primitive definitions and interpretation

### 1. `drawdown_60`

Formula:

```text
Close / rolling_max(Close, 60 sessions) - 1
```

Interpretation:

- Values are normally zero or negative.
- A value of zero means the close is at the highest close in the 60-session window.
- A value closer to zero means the instrument is closer to its 60-session high.
- A more negative value means the instrument is farther below that high.

The console TOP 15 is sorted from highest to lowest value, so it shows instruments closest to their 60-session highs. This is distance from a rolling high, not a drawdown from an investor's entry price and not a complete peak-to-trough risk measure.

### 2. `zscore_sma20_20`

Formula:

```text
(Close - SMA20) / rolling_std(Close - SMA20, 20 sessions)
```

The rolling standard deviation uses the sample standard deviation (`ddof=1`).

Interpretation:

- Positive: close is above SMA20.
- Negative: close is below SMA20.
- Larger absolute magnitude: larger deviation from SMA20 relative to recent residual dispersion.

The console TOP 15 is sorted from highest to lowest value. It therefore shows the strongest positive deviations above SMA20. The value is a standardized distance, not a probability or a normally distributed z-test statistic.

### 3. `realized_vol_60`

Formula:

```text
std(daily close returns, 60 sessions, ddof=1) * sqrt(252)
```

Interpretation:

- Annualized historical volatility estimate based on the previous 60 market sessions.
- Higher values indicate greater realized price variability in that window.
- It is a state/risk descriptor, not a forecast of future volatility and not a directional return signal.

The console TOP 15 is sorted from highest to lowest value.

## Console output

The default run prints a separate TOP 15 for each of the three primitives.

For every primitive, the console table includes:

- primitive rank within valid current-panel observations;
- SECID;
- primitive value;
- PIT TOP50 liquidity rank;
- instrument data status.

The number of valid observations is printed for each primitive. If fewer than 15 values are valid, all available observations are shown. Missing values are never replaced with zero.

Primitive ranks are descriptive cross-sectional ranks for the current snapshot only. Rank 1 is the highest value. Percentiles are calculated only among non-missing values for that primitive.

## Ticker inspection

The `--inspect` option asks for SECIDs separated by spaces and prints, for each requested current-panel instrument:

- snapshot date;
- PIT TOP50 liquidity rank;
- bar availability and data status;
- value, rank, and percentile for each core primitive;
- names of primitives with missing values.

This is a read-only inspection. It does not fetch external data, calculate new features, or alter the panel.

## Data and methodology boundaries

- Universe membership is taken from the existing PIT TOP50 panel. The screener does not construct a retrospective universe.
- SECIDs are treated as distinct instrument identifiers. The screener does not merge instruments by issuer, ISIN, or name.
- Feature values are taken from the established primitive feature builder. The screener does not recalculate or modify them.
- The feature builder uses adjusted close history and the established TQBR/EQBR board-selection logic.
- No price forward-fill is introduced.
- A missing bar or missing primitive remains missing. It is not interpreted as zero, neutral, or a negative signal.
- The panel liquidity rank and primitive ranks are different quantities and must not be conflated.
- Breadth is a separate market-level state family, not an instrument-level primitive. It is intentionally not mixed into the per-ticker CSV or the three primitive rankings. A separate market-state report may expose it.
- The screener does not use forward returns, IC, CAGR, Sharpe, MDD, backtest results, or portfolio weights in its current snapshot.

## Agent usage guidance

Treat the output as structured observations, not decisions.

1. Read `instrument_status` before interpreting any primitive. Do not interpret missing values as zero.
2. Use `panel_rank` only as the instrument's PIT TOP50 liquidity rank.
3. Interpret `drawdown_60` direction correctly: higher values mean closer to the 60-session high.
4. Interpret `zscore_sma20_20` sign and magnitude relative to SMA20 and recent residual dispersion.
5. Interpret `realized_vol_60` as backward-looking realized variability, not a directional forecast.
6. Compare the three dimensions rather than collapsing them into a single screener score.
7. Do not infer a trade, target weight, or portfolio action from a primitive rank alone. Use the downstream agent's approved decision process and other context.
8. The snapshot describes the latest panel date, not necessarily the current wall-clock date.

The screener is a read-only information tool. It must not modify source databases, panel files, primitive feature files, or agent portfolio state.
