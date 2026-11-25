# Watchlist (без механических порогов — не валидированы)

## Убрано (не валидировано)
Breadth>25% вход; z-score<1.5; volume>1.5x; take-profit +6%/SMA20; stop по пробою SMA20. Это narrative, не edge.

## Event / special-sit
- CNRU: оферта T 993.05₽; спред ~9.4% (24.11, close 907.8). Вход только при p_close > breakeven с carry (~42% при downside5%/20d). Вне Model1 top. Deal-risk не оценён → 0%.
- X5: div 204₽, close 2341.5, gross 8.71%/net 7.58%; breakeven gap ~74.5%; реалистичный gap 87–100% → недобор 1.1–2.2% vs LQDT H20 до beta. Выплаты не покрыты FCF. WATCH, не BUY.

## Секторный кластер (одна ставка)
SIBN/TATN/LKOH/RNFT/ROSN/SNGS: corr 120d 0.59–0.86, avg ~0.73; корзина 4 имён снижает vol лишь ~10%. Model1 top, но unvalidated; причина синхронных просадок не установлена. Не диверсифицировать внутри кластера.

## Отдельные имена
- YDEX: dd −15.31%, z −2.14; repricing vs bounce не валидирован; катализатора нет. WATCH.
- POSI: z +0.33, vol 34.6%; edge нет.
- SBER: vol 16.34% (lowest), dd −4.32%; beta-headwind regime, катализатора нет.
- T/GCHE: пользователь вышел 25.11; re-entry только на own issuer/price/event evidence + validated edge vs LQDT.

## Model1
composite=tp_raw×(1−sl_raw); НЕ E[ret]/вероятность. Нужен OOS IC/hit-rate vs LQDT + sector-neutral + turnover/costs. Без истории score валидация невозможна → только поиск.