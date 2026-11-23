# Primitive Research: Design, Results, and Hypotheses

Last updated: 2026-11-23

## Research objective

Build a compact set of interpretable primitives that describe the current state of instruments in the PIT TOP50 universe. The intended downstream use is to help an agent evaluate positions it already holds and understand whether an instrument's state is improving, deteriorating, or changing regime.

This is an information layer, not a standalone trading strategy, signal-to-weight optimizer, or automatic trading system.

## Agreed research scope

- Start with a predefined primitive pack; do not mine an unlimited feature universe.
- No sentiment data.
- No linear regression.
- No Hurst exponent.
- No IMOEX for now. A 20-session return relative to MCFTR is not currently supported by the agreed benchmark/data setup, and IMOEX has a one-session data delay.
- Breadth is a separate market-state family, not an instrument-level cross-sectional feature.
- Primitive evaluation must include information content, stability, coverage, and redundancy. Statistical significance alone is insufficient.

## Current experiment

GitHub file:
- `scripts/experiments/primitives/01_research_report.py`

Latest known performance change:
- Commit `df242a1e0971c8ec3286cafcd923c3507c967dd9` vectorized daily IC calculations.
- Replaced Python loops over each date with NumPy grouped Pearson calculations and vectorized per-date ranking.
- Synthetic equivalence test against the prior per-group Pandas implementation: maximum Pearson difference 2.78e-16; maximum Rank IC difference 1.11e-16.
- This is an algorithmic equivalence test on synthetic data, not a benchmark of full production data execution time.

## Universe and outcome policy

- Signal-date universe is strictly historical PIT TOP50 membership from `top50_panel.parquet`.
- Adjusted bars outside TOP50 are loaded only for lookback history and forward outcome measurement of tickers already selected on the signal date. This does not expand the signal-date universe.
- Features are evaluated only for signal-date rows with `bar_available == 1`.
- Exclusions: GAZC, GAZS, GAZT; suspension interval 2022-02-28 through 2022-03-23.
- Historical series is reindexed to the TQBR/EQBR market calendar. No price forward-fill; missing closes remain missing.
- After the first actual observation, missing ticker/session turnover contributes zero, matching the panel activity convention. Before the first observation, turnover remains unknown.
- Board activity: value and adjusted volume are summed across TQBR/EQBR. OHLC comes from a single complete/valid row, with TQBR priority and EQBR fallback.
- Cross-sectional RS ranks are calculated only inside the PIT TOP50 cohort for each signal date; rank 1 means strongest.

Forward return definition:
`forward_return_H = Close[T+H] / Open[T+1] - 1`, for H = 5, 10, 20 sessions.
Signal is formed after close T; outcome begins at next-session open. This is an execution proxy, not a complete backtest. Transaction costs, spread, slippage, liquidity constraints, and portfolio construction are not included.

## Predeclared cross-sectional primitives (20)

1. `price_sma20`: Close / SMA20 - 1.
2. `sma20_sma50`: SMA20 / SMA50 - 1.
3. `sma50_sma200`: SMA50 / SMA200 - 1.
4. `return_5`: Close / Close shifted 5 sessions - 1.
5. `return_20`: Close / Close shifted 20 sessions - 1.
6. `return_60`: Close / Close shifted 60 sessions - 1.
7. `realized_vol_20`: standard deviation of daily close returns over 20 sessions × sqrt(252).
8. `realized_vol_60`: standard deviation of daily close returns over 60 sessions × sqrt(252).
9. `drawdown_20`: Close / rolling 20-session maximum close - 1.
10. `drawdown_60`: Close / rolling 60-session maximum close - 1.
11. `turnover_ratio_20`: current session turnover / rolling 20-session mean turnover.
12. `rs_rank_20`: cross-sectional rank of 20-session return within PIT TOP50; 1 = strongest.
13. `rs_rank_60`: cross-sectional rank of 60-session return within PIT TOP50; 1 = strongest.
14. `rebound_20`: Close / rolling 20-session minimum close - 1.
15. `rebound_60`: Close / rolling 60-session minimum close - 1.
16. `zscore_sma20_20`: (Close - SMA20) / rolling 20-session standard deviation of that residual.
17. `momentum_acceleration_20`: 20-session return minus its value 5 sessions earlier.
18. `efficiency_ratio_20`: absolute net 20-session price move / sum of absolute one-session moves over 20 sessions.
19. `up_down_turnover_ratio_20`: average turnover on positive-return days / average turnover on negative-return days over 20 sessions.
20. `positive_turnover_share_20`: turnover on positive-return days / total turnover over 20 sessions.

## Breadth primitives (5)

- `breadth_sma20`, `breadth_sma50`, `breadth_sma200`: share of valid signal-date TOP50 members trading above their corresponding moving average.
- `breadth_change_5`: 5-session change in `breadth_sma20`.
- `breadth_change_20`: 20-session change in `breadth_sma20`.

Breadth outcomes are equal-weight mean forward returns of the TOP50 cohort selected on that signal date. A ticker does not need to remain TOP50 after the signal date to contribute its forward outcome.

## Evaluation method

Cross-sectional:
- Daily Pearson IC and Spearman Rank IC for each primitive/horizon.
- At least 20 valid securities per date.
- IC IR = mean daily IC / standard deviation of daily IC; not annualized.
- Newey-West/HAC test with lag up to H-1 and a two-sided normal-approximation p-value.
- Benjamini-Hochberg q-values calculated separately for IC and Rank IC test families.
- Stability periods: 2005-2012, 2013-2019, 2020+.

Breadth:
- Time-series Pearson and Spearman correlation against equal-weight forward returns of the signal-date TOP50 cohort.
- HAC tests and BH q-values.
- Minimum forward coverage: 20 securities; report average forward coverage.

These are first-pass diagnostics. Overlapping forward horizons and time dependence mean inference needs careful interpretation.

## User-run report state

The user ran the report script and supplied the generated report. Panel period: 2005-01-11 to 2026-11-20; 203,053 panel rows; 198,819 signal rows with a current bar; 20 cross-sectional and 5 breadth primitives.

Selected first-pass results (mean daily IC / Rank IC, horizon 20 unless otherwise stated):
- `drawdown_60`: IC +0.05352; Rank IC +0.06389. Because the feature is Close / rolling-high - 1 (usually non-positive), a higher value means closer to the rolling high. Tentative interpretation: proximity to highs is associated with stronger forward returns, consistent with trend persistence.
- `realized_vol_60`: IC -0.04368; Rank IC -0.03491. Higher realized volatility is associated with lower forward returns.
- `zscore_sma20_20`: IC +0.03612; Rank IC +0.03487. Being above the 20-day average relative to recent residual dispersion is positively associated with future returns.
- `drawdown_20`: IC +0.03684; Rank IC +0.04460.
- `positive_turnover_share_20`: IC +0.03360; Rank IC +0.03008.
- `sma50_sma200`: IC +0.05126; Rank IC +0.05535; relationship weakens across periods (IC approx +0.084 in 2005-2012, +0.0368 in 2013-2019, +0.0089 in 2020+).
- `realized_vol_20`: IC -0.0224; Rank IC -0.0299.
- `return_20`: IC +0.0319; Rank IC +0.0342.
- `rs_rank_20`: IC -0.04044; Rank IC -0.03419. Rank 1 is strongest, so negative IC means lower rank numbers / stronger past-return ranks were associated with higher forward returns. This is not an accidental inversion. However, its sign was unstable: 2005-2012 IC approx +0.0335, then negative in 2013-2019 (-0.0314) and 2020+ (-0.0402).
- `rs_rank_60`: weaker negative association, later periods stronger than early period.
- `sma20_sma50`: modest positive association.
- `return_5`, `return_60`: mostly weak.
- `rebound_20/60`, `turnover_ratio_20`, `efficiency_ratio_20`, `momentum_acceleration_20`, `up_down_turnover_ratio_20`: weak or statistically insignificant in the first pass. `return_5` Rank IC showed some significance despite weak Pearson IC.

Breadth first-pass observations (exact values from the user-provided report):
- `breadth_change_5`: Pearson correlation +0.09098 (H5), +0.06743 (H10), +0.05843 (H20); Spearman +0.08489, +0.07263, +0.07632. BH q-values: Pearson 0.01271 / 0.09291 / 0.11610; Spearman 0.00825 / 0.02535 / 0.02535. Thus H5 survives BH for both methods; H10/H20 survive only for Spearman, not Pearson.
- `breadth_change_20`: H5 Pearson +0.07139 and Spearman +0.07608, but BH q-values are 0.09291 and 0.02535 respectively. H10/H20 are not significant after BH.
- `breadth_sma20`: H5 Pearson +0.07804 and Spearman +0.07935; BH q-values 0.09291 and 0.02535 respectively. H10/H20 are not significant after BH.
- `breadth_sma50` and `breadth_sma200`: weak in the first pass.
- Average forward coverage for breadth was about 43.4 securities.

Treat all numbers above as first-pass descriptive results from the user's report, not final selected-feature claims. Re-open the actual report/output files if exact q-values, sample counts, or confidence intervals are needed.

## Initial hypotheses, not decisions

1. Trend/persistence family may be useful: drawdown_60, sma50_sma200, zscore_sma20_20, return_20.
2. Volatility may add a distinct risk/state dimension: realized_vol_20/60.
3. Cross-sectional relative strength may be useful but needs stability scrutiny, especially rs_rank_20's early-period sign reversal.
4. Positive turnover share may capture accumulation/participation quality, but needs robustness checks.
5. Breadth change over 5 sessions may provide a market-state overlay distinct from instrument-level features.
6. Some apparently strong features may be redundant; choose by orthogonality and robustness, not by sorting one IC table.

## Required diagnostics before selecting a primitive pack

1. Re-check feature formula and sign for every leading feature.
2. Produce decile/quantile forward-return analysis by horizon; inspect monotonicity and tails.
3. Compute cross-feature correlation/redundancy matrix, including rank correlations.
4. Review period stability, sample coverage, and missingness.
5. Test sensitivity to extreme observations, liquidity/turnover groups, and relevant subperiods without deleting plausible raw events.
6. Review breadth separately from cross-sectional features.
7. Only then propose a small orthogonal pack and ask the user to approve/reject it.

## Production screener (2026-11-23)

A read-only descriptive screener has now been added:

- Script: `scripts/tools/01_primitive_screener.py`
- Agent documentation: `docs/tools/01_primitive_screener.md`
- Output: `data/interim/screener/latest_primitive_snapshot.csv`
- Current cohort: latest date in the PIT TOP50 panel; one row per panel member, including members without an actual bar.
- Instrument-level pack: `drawdown_60`, `zscore_sma20_20`, `realized_vol_60`.
- Console: separate TOP 15 for each primitive.
- Optional `--inspect`: interactive inspection of one or more current-panel SECIDs.
- Breadth remains a separate market-level state family and is not mixed into per-instrument rankings.
- The screener does not calculate a composite score, trading signal, portfolio weight, or action.
- The tool reads the prepared primitive feature frame; it does not recalculate features or mutate source data.

The tool is committed to GitHub. Local execution and output validation remain pending user-run confirmation.


## Screener: роль, выход и границы интерпретации

Подробная спецификация для downstream-агента находится в `docs/tools/01_primitive_screener.md`. Скринер — runtime-инструмент состояния, не исследовательский отчёт: он выводит текущие значения трёх утверждённых примитивов по последнему PIT TOP50 срезу и не рассчитывает статистику связи с forward returns.

Важно различать три слоя:
1. Runtime snapshot: текущие значения примитивов, их поперечные ранги/перцентили, PIT liquidity rank и статусы пропусков.
2. Исследовательская валидация: IC, Rank IC, IC IR, HAC/Newey-West, p-values, BH q-values, coverage, периодная устойчивость, квантильные/децильные профили, корреляции и проверки утечки/смещений.
3. Портфельные прикладные эксперименты: CAGR, terminal wealth, Sharpe, MDD, exposure, turnover, transaction costs, missing return weight, вклад тикеров/дат и stress-тесты концентрации.

Слой 2 проверяет информационное содержание и устойчивость эффекта. Слой 3 иллюстрирует возможное применение информации в конкретной портфельной конструкции, но не является критерием истинности эффекта. Не оптимизировать исследовательские примитивы по CAGR/Sharpe/MDD и не отвергать эффект только из-за слабой доходности симуляции. Решение о применении информации относится к downstream-агенту.

Идентичность инструмента определяется SECID. Разные SECID не склеиваются по эмитенту, ISIN или названию без отдельного явного правила пользователя.

### Runtime representation of the approved breadth pack (2026-11-23)

The production screener exposes only two market-level values, in a separate `MARKET BREADTH` block:

- `breadth_change_5`: `breadth_sma20[T] - breadth_sma20[T-5]`, an absolute five-trading-session change interpreted in percentage points. This is the primary breadth value.
- `breadth_sma20`: share of valid signal-date PIT TOP50 members with `price_sma20 > 0`, shown for reference only.

Definitions match `build_breadth_frame` in `scripts/experiments/primitives/01_research_report.py`. The daily denominator includes only PIT TOP50 members with `bar_available == 1`; only valid `price_sma20` values enter the proportion. Missing bars and unavailable SMA20 values are not treated as below-SMA observations. The five-session change uses `diff(5)` on the panel trading-date calendar, with no forward-fill.

The screener does not expose breadth_sma50, breadth_sma200, breadth_change_20, daily advancing share, or any additional breadth indicators. Breadth remains a separate descriptive market-state layer, not part of per-instrument TOP15 rankings or a composite score.


## Breadth allocation heuristic: application boundary (2026-11-23)

A separate portfolio application experiment used the approved breadth state to scale base exposure:

| Breadth level | Five-session breadth change | Exposure multiplier |
|---|---|---:|
| >= 50% | Rising (> 0) | 100% |
| >= 50% | Flat/falling (<= 0) | 75% |
| < 50% | Rising (> 0) | 50% |
| < 50% | Flat/falling (<= 0) | 25% |

This schedule is a **user-proposed heuristic**, not a statistically estimated or optimized risk model. The user observed that this direction of exposure scaling reduced drawdown in the tested portfolio application. Treat that as an experiment-specific observation, not proof of causality, robustness, or optimality. It may be considered as market-state context when a downstream process decides allocation size, but the screener itself does not apply the multipliers or make portfolio decisions.

**Implementation audit item:** the current portfolio experiment's scripts/experiments/primitives/portfolios/data.py classifies the upper regime with breadth_level > 50.0, while the agreed user rule is breadth_sma20 >= 50%. Exactly 50% is therefore classified differently in code than in the documented rule. Do not silently treat the implementation and specification as identical. Resolve the boundary before relying on or rerunning the four-regime experiment.
