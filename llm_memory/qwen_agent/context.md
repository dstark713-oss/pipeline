# Qwen Agent — рабочий контекст (обновлено 2026-11-26)

## Роль
Адверсариальный критик ежедневного trading-loop (ChatGPT = trading_agent). НЕ со-решатель, НЕ сигнал/authority. Независимый анализ ДО handoff. Канон: trading_agent/06_DAILY_TRADING_RESEARCH_LOOP.md + QWEN_HANDOFF.md.

## Мандат
- Горизонты H1/H5/H20. Вопрос: что LONG/SHORT сегодня, на каком горизонте, каким обоснованным размером.
- Активные действия: LONG или SHORT. **HOLD запрещён как label.** Нейтраль = LONG LQDT (opportunity-cost).
- Бенчмарк LQDT: для backtest — date-matched HISTORICAL LQDT (next-open→horizon-close); для forward opportunity cost — current trailing. НЕ смешивать.
- Ключевая ставка 14%, следующее заседание 18.12.2026.

## Текущее фактическое состояние (user-reported)
- 25.11.2026: ПОЛНЫЙ ВЫХОД В КЭШ (~100% LQDT/cash). Подтвердить точный snapshot.
- Baseline 23.11 (T10/GCHE2/LQDT88) — ТОЛЬКО история, не текущая аллокация.
- Никогда не выводить исполнение из рекомендации.

## Данные / инструменты
- PIT TOP50 panel: data/processed/top50/top50_panel.parquet + top50_membership.parquet (tradedate, ranking_asof_date, secid, value_60d, rank, universe_size, selection_method).
- Loader: scripts/dataset/05_build_top50_panel.py (load_source_data, aggregate_boards, build_membership, build_panel).
- LQDT НЕ в adjusted SQLite/top50 panel. Тянуть отдельно MOEX ISS **/candles** (НЕ /history), ожидаемый board TQTF. Мой прошлый fetch через TQBR — reconcile. При сбое → NOT ASSESSABLE.
- scripts/cache: LQDT history cache downloader. scripts/tools/00_refresh_ds.py: daily refresh.
- Repair overlay: 06_repair_incomplete_bars.py + 04_build_adjusted_dataset.py (committed, NOT runtime-tested).
- Model1: CatBoost ensemble на triple-barrier; composite=tp_raw×(1−sl_raw); НЕ калиброванная E[ret]; ранг≠BUY.

## Research direction (DS-first)
- Trader TA исключён (ATR/RSI/MACD/Bollinger/stochastic/candles).
- ML Direction: PIT TOP50, 5-session binary target, features≤close(t), walk-forward expanding 3yr, monthly retrain, purging.
- Rolling Statistical Moments family CLOSED 25.11 — не открывать без запроса.
- EDA v2 plan (ACF signed/abs/squared, Ljung-Box BH, cross-sectional dependence, dispersion, rank mobility) — proposed, awaits approval.
- Нет internal fundamental dataset; external — только с PIT provenance.

## Capability boundary
- Читаю репо (web_extractor) ✓. Пушу/коммичу ✗. Скрипты исполняет пользователь локально; code в GitHub ≠ evidence of execution.