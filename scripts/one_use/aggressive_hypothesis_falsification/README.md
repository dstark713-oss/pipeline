# Aggressive Hypothesis Falsification

Runs four falsification modules after the initial market snapshot and confirmation pass. This stage does not generate trade directions or position sizes.

## Run

From the repository root:

```powershell
git pull
python scripts/one_use/aggressive_hypothesis_falsification/run_hypothesis_falsification.py
```

## Inputs

- `data/interim/aggressive_market_snapshot/market_snapshot.parquet`
- `data/interim/aggressive_market_snapshot/equal_weight_top50_benchmark.parquet`
- `data/processed/moex_daily_adjusted.sqlite`, table `adjusted_daily_bars`

The module imports the market-snapshot builder to reuse its adjusted-board aggregation policy and suspension dates.

## Forward-return convention

The global adjusted-market calendar is the sorted set of dates with adjusted bars. For a signal on session `t`, ticker forward return at horizon `h` is:

`adjusted_close[t+h] / adjusted_close[t] - 1`

where `t+h` means exactly h rows later on the global market calendar. Missing ticker closes at either endpoint remain missing. No ticker-specific next-observation substitution and no price forward-fill are allowed. The benchmark compounds daily equal-weight PIT TOP50 returns from sessions `t+1` through `t+h`.

## Four modules

1. **F1, incremental RS20:** compare top-quintile RS20 names with peers inside the same RS5 quintile; also run date-wise cross-sectional regressions of forward RS on standardized RS20, RS5, and realized volatility20.
   - Identification constraint: RS20 and absolute return20 are perfectly collinear within a date; the same is true of RS5 and absolute return5. RS5 therefore serves as the equivalent cross-sectional control for absolute 5D performance, with realized volatility20 as an additional non-collinear control. The model does not claim to separately identify either RS/absolute-return pair.
2. **F2, aligned momentum:** report all four sign quadrants of absolute 5D and 20D returns; estimate a date-wise interaction model with both standardized horizons and their product.
3. **F3, persistent weakness:** compare simultaneous bottom-quintile RS5/RS20 weakness with RS5-only weakness, RS20-only weakness, and the remaining valid cross-section. Also report robustness outside predefined stress windows: 2008-09-15..2009-06-30, 2020-02-20..2020-06-30, and 2022-02-24..2022-12-30.
4. **F4, impulse concentration:** within the positive 5D-return top quintile, split names by the date-wise median of the largest absolute daily log-return share; compare forward relative performance, hit rate, and negative-return frequency; also regress forward RS on concentration and 5D return within the impulse group to test whether concentration adds information beyond impulse magnitude.

## Inference

Daily cross-sectional contrasts are calculated first. HAC Newey-West inference and circular moving-block bootstrap are then applied to the date-level series. Resampling dates rather than individual securities preserves contemporaneous cross-sectional dependence within each date. Forward horizons overlap; the NW lag is conservatively set to 19 sessions. The twenty-session block bootstrap is a robustness interval, not an exact finite-sample test.

Historical subperiods are fixed as through 2012, 2013-2019, and 2020 onward. Crisis exclusions are robustness diagnostics, not the primary sample.

## Outputs

One Markdown report:
- `docs/aggressive_hypothesis_falsification_report.md`

Machine-readable outputs:
- `data/interim/aggressive_hypothesis_falsification/`

The script writes CSVs for daily contrasts, regression coefficients and summaries, quadrant outcomes, concentration metrics, and period stability. Console output is intentionally limited to a compact run summary.

## Decision boundary

This module only falsifies or retains research hypotheses. If a hypothesis survives, a separate step is required to form a name-level candidate signal. It does not create BUY/SELL instructions, target weights, leverage, short exposure, or portfolio sizing.
