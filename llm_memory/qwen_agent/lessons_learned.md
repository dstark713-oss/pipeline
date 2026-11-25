# Уроки (append-only)

## 2026-11-24 L1 — фреймворк
Долгосрочный инвест-анализ применён к 1-20d; ставка не подтянута (16-18% вместо 14%). Урок: уточнять горизонт/ставку; <30d — без облигаций/флоатеров/долгосрочного фундаментала.

## 2026-11-24 L2 — нарратив vs гипотеза
Трейдерский фольклор выдан за аналитику без кода. Урок: нетривиальное утверждение = hypothesis + script; IC≈0 → отозвать; уровни без evidence = шум.

## 2026-11-25 L3 — MAJOR: breadth-trim overclaim фальсифицирован
Мой вывод «при breadth 8% E[equity]<LQDT, CI ниже → trim T5/GCHE0» ОТОЗВАН.
Ошибки:
(a) Benchmark mismatch: historical conditional equity vs CURRENT trailing LQDT. Нужен date-matched historical LQDT (next-open→horizon-close).
(b) Mean-CI выдан за prediction interval; HAC/regime clustering не учтены.
(c) Episode-bootstrap: H5/H20 всего 7/4 валидных кластера → все интервалы excess включают 0 (T/GCHE/EW-TOP50).
(d) False-precision sizing без T-beta/alpha/оптимизации.
(e) GCHE вне TOP50 ≠ sell-сигнал.
Corrected (user-run paired-excess audit): low-breadth excess vs matched LQDT НЕ валидирован ни на одном горизонте; 20d HAC незначим (t 1.26→0.41); бакеты немонотонны; WF хуже baseline (MAE/RMSE, corr ~0.035/−0.134). Breadth — descriptive regime warning, НЕ tradable timing rule.

## 2026-11-25 L4 — raw IC ≠ validated edge
daily_report primitive IC (pos60d +0.054, z20 +0.036, vol −0.044, RS −0.040) — raw point estimates. Мой PIT TOP50 NW-test: z_dist/vol60 незначимы (NW_t 0.03–0.17). Reconcile: universe/horizon/IC def (Pearson vs Spearman, pooled vs XS)/significance. Breadth: time-series info для index (мой H1) ≠ cross-sectional info (research: static adds none) — разные вопросы, не противоречие.

## 2026-11-25 L5 — данные/исполнение
ISS: /candles НЕ /history. LQDT board ожидаемо TQTF (мой TQBR fetch reconcile). Code в GitHub ≠ execution. User actual (full cash 25.11) может расходиться с agent rec — никогда не выводить исполнение из рекомендации. Grade process, не только outcome.

## 2026-11-26 L7 — Model1 composite REJECT при r=1.5 (TP 1.5σ / SL 1σ)
Payoff = 1.5·tp_hit − sl_hit: ВСЕ децили < 0; лучший dec9 −0.0211 (breakeven r 1.59 > 1.5); overall −0.0765.
Top−bottom spread +0.059 = слабое относительное ранжирование, абсолютного edge нет.
Composite ≈ activity/vol score; (1-p_sl) не инвертирует SL (AUC vs sl_hit 0.577).
REJECT как positive LONG prior. Top Model1 ranks = activity/SL-heavy, не edge. Нейтраль LONG LQDT.
Inverse/SHORT — отдельная невалидированная гипотеза, не авторизована.