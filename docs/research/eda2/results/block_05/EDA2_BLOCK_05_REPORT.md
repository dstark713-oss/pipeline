# EDA2 — Блок 5. Неоднородность масштаба и волатильности

## Выборка
- Даты панели: 5,490
- Бумаг: 214
- Наблюдений доходности: 196,663
- Период: 5,489 panel sessions

## Распределение rolling scale

| Окно | Метрика | N | Median | Q10 | Q25 | Q75 | Q90 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 20 | rolling_std | 183108 | 0.0175917 | 0.00967648 | 0.0129552 | 0.0240758 | 0.0335195 |
| 20 | rolling_mad | 183108 | 0.00981393 | 0.00489426 | 0.00691708 | 0.0138183 | 0.018943 |
| 60 | rolling_std | 165643 | 0.0185304 | 0.0113902 | 0.0143825 | 0.0245167 | 0.0327572 |
| 60 | rolling_mad | 165643 | 0.010051 | 0.00584895 | 0.00765219 | 0.0132013 | 0.016796 |
| 120 | rolling_std | 149189 | 0.0191015 | 0.0123744 | 0.0150674 | 0.024569 | 0.0309486 |
| 120 | rolling_mad | 149189 | 0.0100191 | 0.0062115 | 0.0079351 | 0.0125952 | 0.015338 |
| 240 | rolling_std | 125481 | 0.0195107 | 0.0132629 | 0.0158604 | 0.0238387 | 0.0287883 |
| 240 | rolling_mad | 125481 | 0.00991822 | 0.00663002 | 0.00812002 | 0.0120037 | 0.0141149 |

## Временная изменчивость внутри бумаги
Per-security temporal summaries (median, quantiles, temporal IQR/range) находятся в per_security_temporal_variability.csv.
## Устойчивость относительного масштаба между периодами
Rank correlations сравнивают медианный rolling scale каждой бумаги в двух периодах, по общим бумагам.

| Окно | Метрика | Периоды | N | Spearman | Pearson |
|---:|---|---|---:|---:|---:|
| 20 | rolling_mad | 2005_2012 vs 2013_2019 | 29 | 0.41133 | 0.57857 |
| 20 | rolling_mad | 2005_2012 vs 2020_2026 | 21 | 0.24935 | 0.37503 |
| 20 | rolling_mad | 2013_2019 vs 2020_2026 | 61 | 0.25378 | 0.25003 |
| 20 | rolling_std | 2005_2012 vs 2013_2019 | 29 | 0.42956 | 0.54039 |
| 20 | rolling_std | 2005_2012 vs 2020_2026 | 21 | 0.53377 | 0.51789 |
| 20 | rolling_std | 2013_2019 vs 2020_2026 | 61 | 0.46732 | 0.53353 |
| 60 | rolling_mad | 2005_2012 vs 2013_2019 | 27 | 0.31319 | 0.37126 |
| 60 | rolling_mad | 2005_2012 vs 2020_2026 | 19 | -0.07368 | 0.07146 |
| 60 | rolling_mad | 2013_2019 vs 2020_2026 | 55 | 0.40967 | 0.54233 |
| 60 | rolling_std | 2005_2012 vs 2013_2019 | 27 | 0.47558 | 0.53053 |
| 60 | rolling_std | 2005_2012 vs 2020_2026 | 19 | 0.21228 | 0.30585 |
| 60 | rolling_std | 2013_2019 vs 2020_2026 | 55 | 0.51075 | 0.72420 |
| 120 | rolling_mad | 2005_2012 vs 2013_2019 | 25 | 0.61769 | 0.62665 |
| 120 | rolling_mad | 2005_2012 vs 2020_2026 | 19 | 0.01404 | 0.03312 |
| 120 | rolling_mad | 2013_2019 vs 2020_2026 | 48 | 0.40219 | 0.56212 |
| 120 | rolling_std | 2005_2012 vs 2013_2019 | 25 | 0.61769 | 0.72189 |
| 120 | rolling_std | 2005_2012 vs 2020_2026 | 19 | -0.06667 | 0.05437 |
| 120 | rolling_std | 2013_2019 vs 2020_2026 | 48 | 0.38200 | 0.79646 |
| 240 | rolling_mad | 2005_2012 vs 2013_2019 | 18 | 0.81837 | 0.83498 |
| 240 | rolling_mad | 2005_2012 vs 2020_2026 | 12 | 0.13287 | 0.31300 |
| 240 | rolling_mad | 2013_2019 vs 2020_2026 | 46 | 0.50663 | 0.51948 |
| 240 | rolling_std | 2005_2012 vs 2013_2019 | 18 | 0.66357 | 0.74362 |
| 240 | rolling_std | 2005_2012 vs 2020_2026 | 12 | 0.41259 | 0.47092 |
| 240 | rolling_std | 2013_2019 vs 2020_2026 | 46 | 0.51748 | 0.59819 |

## Ограничения
- Rolling estimates require complete windows; no imputation or gap stitching.
- MAD is unscaled median absolute deviation.
- Rank correlations describe cross-period stability, not causal persistence or predictive utility.
- The 2020–2026 period is incomplete.
- No GARCH, forecasting, models, IC, feature selection or trading conclusions.

## Outputs
- rolling_scale_distribution_summary.csv
- per_security_temporal_variability.csv
- period_security_scale.csv
- cross_period_rank_stability.csv
- EDA2_BLOCK_05_REPORT.md
