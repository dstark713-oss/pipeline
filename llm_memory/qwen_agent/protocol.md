# Протокол (калиброванный LONG/SHORT loop, 25.11)

## Evidence labels (стандарт репо)
User-reported | User-run result | Live external source | Verified in repository | Inference | Hypothesis | Unknown/unavailable.
(Мои старые [FACT]/[HYPOTHESIS]/[UNVERIFIED_PRIOR] мапплю на эти; NARRATIVE запрещён как опора.)

## Что я обязан оспорить (QWEN_HANDOFF, 8 пунктов)
1. Edge реален, PIT-valid, сильнее LQDT после издержек?
2. Data/labels/dates/horizons/benchmarks выровнены?
3. Гипотеза фальсифицируема или narrative post-hoc?
4. Sample size / dependence / regime clustering / uncertainty честно учтены?
5. Size следует из evidence+risks или arbitrary?
6. Какие LONG/SHORT альтернативы / LONG LQDT упущены?
7. Что инвалидирует тезис; где reasoning выходит за validated boundary?
8. Какие ветки decision-tree unsupported → remove.

## Возврат
Strongest objections; missing tests/data; factual claims needing verification; alternative directional hypotheses; sizing critique; per-branch verdict: survives / revise / reject. НЕ generic bear/base/bull.

## Запрещено
- Narrative как опора; unverified prior как recommendation.
- Механические пороги/множители без валидации (breadth 25%, 2σ, 1.5x volume).
- False-precision sizing без beta/alpha/оптимизации.
- Benchmark mismatch (current vs historical LQDT).
- Mean-CI выдавать за prediction interval.
- Игнорировать regime clustering / overlapping horizons / малые episode counts.
- Universe-exclusion как sell-сигнал.
- Выводить исполнение из рекомендации.

## Sizing (обязателен, из evidence)
Expected excess vs LQDT на горизонте; uncertainty/downside; vol/covariance; liquidity/spread/turnover/capacity/costs; signed-exposure constraints; robustness. Не из prior ownership / small size / round %. Нет обоснованного размера → 0 и LONG LQDT.

## Script policy
≤2 passes/phase (run + analysis), ≤2 post-Qwen. ≤linear без approval; read-only; fixed inputs/cutoffs; compact output; ≥1 новая фальсифицируемая гипотеза или явное объяснение почему нет. Не permanent pipeline.

## Минимальный артефакт
Facts (labeled) + falsifiable hypothesis + script + data-derived decision rule + dependence-aware uncertainty + invalidation.