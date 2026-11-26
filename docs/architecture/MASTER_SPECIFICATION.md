# QUANT RESEARCH PIPELINE — MASTER SPECIFICATION

> Canonical source transferred into `dstark713-oss/pipeline/docs/architecture/` on 2026-11-26. The original 17-stage specification is preserved below. The architecture governance update dated 2026-11-27 at the end of this document is authoritative for the current operating model and supersedes legacy agent-role descriptions in the original stage text.

## Задача

Спроектировать и последовательно реализовать полноценный Quant Research Pipeline для systematic multi-asset position trading.

Pipeline состоит ровно из 17 последовательных исследовательских и производственных этапов.

Это единый сквозной процесс: от определения рынка и получения данных до production deployment, live trading, performance attribution и эволюции торговых агентов.

Не сокращай этапы, не объединяй их и не добавляй новые этапы без отдельного архитектурного обоснования.

Для каждого этапа необходимо определить:
- назначение и границы ответственности;
- входные данные и зависимости;
- конкретные исследовательские задачи;
- методы и инструменты;
- процедуры контроля качества;
- критерии успешного завершения;
- условия отклонения результатов;
- выходные артефакты;
- зависимости от предыдущих и последующих этапов.

Pipeline должен быть воспроизводимым, модульным, artifact-driven и пригодным для автоматизации.

---

## STAGE 01 — Market & Universe Definition

**Цель:** формально определить исследуемый рынок и universe инструментов.

Содержание:
- Asset Class Definition.
- Instrument Universe.
- Market Coverage.
- Liquidity Requirements.
- Trading Sessions.
- Exchange Calendars.
- Contract Specifications.
- Historical Universe Reconstruction.
- Instrument Inclusion/Exclusion Rules.
- Delisted and Expired Instruments.
- Point-in-Time Universe Integrity.

Необходимо учитывать специфику различных классов активов: futures, equities, ETFs, FX, rates, commodities, indices и других при необходимости.

**Output:**
- `universe_specification`
- `instrument_master`
- `market_calendar`
- `contract_specification_registry`

## STAGE 02 — Data Acquisition

**Цель:** организовать получение исходных рыночных и фундаментальных данных.

Источники и типы данных:
- OHLCV.
- Open Interest.
- Volume.
- Futures Term Structure.
- Individual Futures Contracts.
- Continuous Futures Data.
- Contract Specifications.
- Macro Data.
- Interest Rates.
- Yield Curves.
- Positioning Data.
- Fundamentals.
- Alternative Data.

Принципы:
- Биржи и первичные источники имеют приоритет.
- Сторонние агрегаторы используются как fallback.
- Хранить provenance каждого набора данных.
- Разделять raw data и обработанные данные.
- Поддерживать историческую загрузку и регулярное обновление.
- Контролировать задержки, полноту и доступность источников.

Для каждого источника определить:
- API или способ получения;
- доступную глубину истории;
- частоту обновления;
- ограничения;
- стоимость;
- лицензионные условия;
- fallback source.

**Output:**
- `raw_market_data`
- `data_source_registry`
- `acquisition_logs`

## STAGE 03 — Data Engineering & Quality Control

**Цель:** преобразовать исходные данные в качественные исследовательские datasets.

Содержание:
- Data Cleaning.
- Data Normalization.
- Timestamp and Timezone Standardization.
- Exchange Calendar Alignment.
- Missing Data Handling.
- Outlier Detection.
- Duplicate Detection.
- Currency Conversion.
- Corporate Actions.
- Futures Contract Stitching.
- Futures Roll Adjustment.
- Continuous Contract Construction.
- OHLCV Aggregation and Resampling.
- Cross-Asset Alignment.
- Data Quality Metrics.
- Dataset Versioning.

Особое внимание:
- не допускать использования будущей информации;
- не смешивать реальные контрактные цены с искусственно скорректированными continuous series без явного обозначения;
- сохранять связь между continuous contract и исходными контрактами;
- обеспечивать воспроизводимость исторических datasets.

**Output:**
- `validated_datasets`
- `data_quality_report`
- `continuous_contracts`
- `dataset_versions`

## STAGE 04 — Exploratory Data Analysis (EDA)

**Цель:** исследовать статистические и структурные свойства рынка до разработки гипотез и моделей.

Содержание:
- Distribution Analysis.
- Descriptive Statistics.
- Return Distribution.
- Volatility Analysis.
- Autocorrelation.
- Cross-Correlation.
- Serial Dependence.
- Seasonality.
- Trend Characteristics.
- Mean Reversion Characteristics.
- Regime Analysis.
- Cross-Sectional Analysis.
- Tail Risk.
- Extreme Events.
- Market Microstructure (если доступны соответствующие данные).
- Futures Curve Characteristics.

Результаты должны описывать:
- характерные свойства каждого инструмента;
- различия между классами активов;
- временную стабильность свойств;
- потенциальные аномалии;
- ограничения и качество данных.

**Output:**
- `eda_report`
- `market_characteristics`
- `instrument_statistics`

## STAGE 05 — Hypothesis Research

**Цель:** формировать экономически и статистически обоснованные исследовательские гипотезы, для которых заранее определён механизм создания экономической ценности.

Stage 05 имеет ровно две категории гипотез:

### I. Risk Control — контроль риска

**Экономическая цель:** сохранить капитал и повысить эффективность его использования.

Исследуются закономерности, которые потенциально позволяют:
- заранее обнаруживать изменение уровня и структуры риска;
- адаптировать рыночную экспозицию;
- снижать концентрацию и совместный риск активов;
- уменьшать тяжесть потерь и просадок;
- улучшать риск-скорректированный результат без искусственного снижения доходности простым уходом в кэш.

Первоначальный пул:
- RC-001 — прогнозирование изменения волатильности и адаптация экспозиции;
- RC-002 — изменение взаимосвязей активов и управление системным риском;
- RC-003 — необычная торговая активность как возможное предупреждение о будущем риске.

### II. Direct Monetization — прямая монетизация

**Экономическая цель:** обнаружить воспроизводимые закономерности, позволяющие получать дополнительную доходность после издержек и ограничений реализации.

Исследуются закономерности, которые потенциально позволяют:
- прогнозировать будущую относительную доходность инструментов;
- отбирать инструменты с положительным ожидаемым преимуществом;
- выявлять устойчивые ценовые, информационные и поведенческие эффекты;
- использовать особенности торговой активности и различия в компенсации за риск.

Первоначальный пул:
- DM-001 — устойчивость относительной доходности инструментов;
- DM-002 — связь торговой активности с будущей относительной доходностью;
- DM-003 — неоднородность рынка как условие расширения возможностей отбора активов;
- DM-004 — компенсация за принятие риска.

### Обязательная структура каждой гипотезы

Для каждой гипотезы документировать:
- уникальный ID и категорию;
- точную формулировку проверяемого утверждения;
- экономический механизм;
- предполагаемое поведение рынка и направление эффекта;
- механизм создания экономической ценности: управление риском или дополнительная доходность;
- инструменты и классы активов;
- временной горизонт;
- необходимые данные и временную доступность данных;
- предполагаемые признаки;
- потенциальные confounding factors (смешивающие факторы);
- условия применимости;
- критерии подтверждения;
- критерии опровержения;
- ограничения реализации, включая ликвидность, комиссии, проскальзывание и оборот;
- основания из EDA и/или независимую экономическую аргументацию;
- статус и приоритет исследования.

### Экономический фильтр

Гипотеза не включается в основной реестр, если отсутствует понятный механизм экономической ценности.

Каждая гипотеза обязана отвечать:
1. Какое поведение рынка предполагается?
2. Почему оно должно возникать?
3. Как именно оно создаёт выгоду?
4. Почему информация может быть доступна до реализации эффекта?
5. Сохраняется ли потенциальная выгода после издержек и ограничений?
6. Какие наблюдения заставят отвергнуть гипотезу?

Гипотезы Risk Control и Direct Monetization оцениваются раздельно. Снижение риска не называется прямой альфой, а положительная историческая доходность не считается доказательством монетизации.

### Методологические ограничения

- EDA предоставляет основания и ограничения, но не доказывает предсказательную способность.
- Разделять EDA-driven гипотезы и mechanism-driven гипотезы. Не ограничивать поиск только переменными, попавшими в EDA.
- Не подменять экономический механизм корреляцией или статистической значимостью.
- До эксперимента фиксировать целевую переменную, горизонт, признаки, контрольные переменные, семейство проверок, метрики и критерии решения.
- Учитывать временную зависимость, PIT-доступность данных, survivorship/selection bias, leakage, множественные проверки и нестабильность режимов.
- Проверять устойчивость во времени и на независимых данных.
- Для Direct Monetization обязательна оценка чистого экономического результата после реалистичных транзакционных издержек.
- Для Risk Control сравнивать адаптивный подход с содержательным базовым вариантом при сопоставимой доходности/экспозиции; простое сокращение вложенного капитала не является достаточным доказательством ценности.
- Не принимать гипотезу только потому, что она показывает хорошую историческую доходность.

### Выходные артефакты

- `research_hypothesis` — паспорта отдельных гипотез, разделённые по двум категориям;
- `hypothesis_registry` — единый реестр, статусы и связи с источниками;
- `research_priority` — обоснованная очередность исследований и критерии приоритизации.

Рабочая документация и результаты этапа хранятся отдельно от паспортов гипотез. Структура и план: `docs/research/hypothesis_research/`.

**Первоначальный согласованный пул:** 3 гипотезы Risk Control и 4 гипотезы Direct Monetization. Их согласование означает разрешение на исследовательскую проработку, но не эмпирическое подтверждение.

## STAGE 06 — Research Design & Method Selection

**Цель:** спроектировать исследование и выбрать подходящие методы проверки гипотезы.

Содержание:
- Target Variable Definition.
- Prediction Horizon.
- Benchmark Definition.
- Research Methodology.
- Statistical Test Selection.
- Candidate Model Families.
- Validation Design.
- Evaluation Metrics.
- Data Requirements.
- Acceptance Criteria.
- Rejection Criteria.
- Computational Requirements.

Возможные методы:
- Descriptive and Inferential Statistics.
- OLS and Linear Models.
- Logistic Regression.
- Time-Series Models.
- GARCH Family.
- Tree-Based Models.
- Random Forest.
- XGBoost.
- Hidden Markov Models.
- Clustering.
- Rule-Based Models.
- Other ML/Statistical Methods where justified.

Метод выбирается исходя из исследовательской задачи, а не из популярности алгоритма.

Здесь определяется пространство допустимых методов, но ещё не выбирается окончательная production-модель.

**Output:**
- `research_design`
- `candidate_method_space`
- `validation_protocol`
- `acceptance_criteria`

## STAGE 07 — Feature Engineering

**Цель:** сформировать исследовательское пространство признаков.

Содержание:
- Feature Discovery.
- Feature Construction.
- Feature Transformation.
- Feature Normalization.
- Rolling Features.
- Lagged Features.
- Cross-Sectional Features.
- Volatility Features.
- Momentum Features.
- Mean Reversion Features.
- Term Structure Features.
- Carry Features.
- Positioning Features.
- Macro Features.
- Regime Features.
- Feature Selection.
- Feature Importance.
- Multicollinearity Analysis.
- Feature Stability.
- Leakage Detection.

Для каждого признака документировать:
- экономический смысл;
- формулу;
- источник данных;
- временную доступность;
- период расчёта;
- допустимые значения;
- правила обработки пропусков;
- версию реализации.

**Output:**
- `feature_dataset`
- `feature_specification`
- `feature_registry`

## STAGE 08 — Signal & Model Development

**Цель:** разработать и реализовать кандидатов моделей и торговых сигналов.

Содержание:
- Signal Construction.
- Model Implementation.
- Model Training.
- Parameter Estimation.
- Baseline Development.
- Candidate Model Development.
- Prediction Generation.
- Directional Classification.
- Forecast Generation.
- Thresholding.
- Signal Calibration.
- Initial Performance Evaluation.

Возможные выходы моделей:
- Directional Forecasts.
- Expected Returns.
- Probabilities.
- Ranking Scores.
- Volatility Forecasts.
- Regime Probabilities.
- Carry Estimates.
- Relative Value Signals.

Важно разделять прогноз модели и торговое решение стратегии.

**Output:**
- `candidate_models`
- `candidate_signals`
- `model_training_reports`

## STAGE 09 — Model Selection & Optimization

**Цель:** выбрать наиболее подходящую модель среди разработанных кандидатов.

Содержание:
- Candidate Model Comparison.
- Hyperparameter Optimization.
- Cross-Validation.
- Baseline Comparison.
- Performance Evaluation.
- Stability Analysis.
- Complexity Analysis.
- Computational Cost Analysis.
- Sensitivity Analysis.
- Model Robustness.
- Champion/Challenger Framework.
- Model Selection.

Оптимизация должна быть защищена от overfitting.

Не выбирать модель исключительно по максимальному историческому Sharpe или доходности.

Учитывать:
- стабильность;
- воспроизводимость;
- сложность;
- чувствительность к параметрам;
- обобщающую способность;
- экономическую интерпретируемость;
- эксплуатационные затраты.

**Output:**
- `selected_model`
- `model_version`
- `experiment_report`
- `model_selection_report`

## STAGE 10 — Alpha Validation

**Цель:** установить, существует ли реальный, устойчивый и экономически значимый alpha.

Содержание:
- Predictive Performance Validation.
- Statistical Significance.
- Multiple Testing Correction.
- Temporal Stability.
- Cross-Sectional Stability.
- Regime Stability.
- Signal Decay.
- Robustness Testing.
- Economic Interpretation.
- Alpha Persistence.
- Capacity Considerations.
- Alternative Explanations.

Разделять:
- статистическую значимость;
- предсказательную способность;
- экономическую значимость;
- реализуемость после транзакционных издержек.

Гипотеза может быть отклонена, даже если отдельные тесты показывают положительные результаты.

**Output:**
- `validated_alpha`
- `alpha_validation_report`
- `alpha_quality_metrics`

## STAGE 11 — Strategy Development

**Цель:** превратить валидированный alpha в формализованную торговую стратегию.

Содержание:
- Strategy Logic.
- Entry Rules.
- Exit Rules.
- Long/Short Logic.
- Holding Period.
- Signal Frequency.
- Rebalancing.
- Position Transition Rules.
- Strategy Parameters.
- Instrument Constraints.
- Trading Calendar.
- Execution Assumptions.
- Strategy State Management.

Необходимо отделять:
- модельный прогноз;
- торговый сигнал;
- правила стратегии;
- портфельное распределение капитала.

Стратегия не должна самостоятельно определять глобальный портфельный риск.

**Output:**
- `strategy_definition`
- `strategy_configuration`
- `strategy_logic_specification`

## STAGE 12 — Backtesting

**Цель:** проверить историческую экономическую эффективность стратегии в реалистичной симуляции.

Содержание:
- Historical Simulation.
- Trade Simulation.
- Position Tracking.
- Transaction Costs.
- Commissions.
- Slippage.
- Market Impact.
- Liquidity Constraints.
- Turnover.
- Trade-Level Analysis.
- Return Attribution.
- Drawdown Analysis.
- Benchmark Comparison.
- Exposure Analysis.
- Portfolio-Level Simulation.

Основные метрики:
- CAGR.
- Annualized Return.
- Volatility.
- Sharpe Ratio.
- Sortino Ratio.
- Calmar Ratio.
- Maximum Drawdown.
- Win Rate.
- Profit Factor.
- Average Trade.
- Turnover.
- Exposure.
- Tail Metrics.

Обязательно учитывать реальные особенности исполнения конкретных инструментов.

**Output:**
- `backtest_report`
- `trade_history`
- `performance_metrics`
- `exposure_report`

## STAGE 13 — Out-of-Sample & Robustness Validation

**Цель:** проверить способность стратегии работать вне выборки разработки и при изменении рыночных условий.

Содержание:
- Train/Validation/Test Separation.
- Out-of-Sample Testing.
- Walk-Forward Analysis.
- Purged Cross-Validation.
- Embargo.
- Bootstrap.
- Monte Carlo.
- Parameter Sensitivity.
- Stress Testing.
- Regime Robustness.
- Alternative Data Assumptions.
- Transaction Cost Sensitivity.
- Execution Sensitivity.
- Parameter Stability.

Необходимо исключить:
- look-ahead bias;
- leakage;
- survivorship bias;
- selection bias;
- data snooping;
- backtest overfitting.

Результат должен определять, выдерживает ли стратегия независимую проверку и какие ограничения применимости у неё есть.

**Output:**
- `oos_validation_report`
- `robustness_report`
- `strategy_validation_status`

## STAGE 14 — Portfolio Construction

**Цель:** объединить валидированные стратегии и возможности в согласованную портфельную структуру.

Содержание:
- Strategy Allocation.
- Cross-Asset Diversification.
- Correlation Analysis.
- Risk Contribution.
- Volatility Targeting.
- Risk Budgeting.
- Portfolio Optimization.
- Capital Allocation.
- Exposure Management.
- Portfolio Simulation.
- Concentration Analysis.

Рассматривать не только отдельные стратегии, но и их совместное поведение.

Учитывать:
- корреляции;
- общие факторы риска;
- пересечение инструментов;
- концентрацию;
- ликвидность;
- доступный капитал;
- маржу;
- совместные просадки.

**Output:**
- `portfolio_model`
- `target_allocations`
- `portfolio_construction_report`

## STAGE 15 — Portfolio Risk Validation

**Цель:** проверить соответствие сформированного портфеля заданному Risk Profile.

Содержание:
- Portfolio Volatility.
- VaR / CVaR.
- Maximum Drawdown.
- Stress Testing.
- Tail Risk.
- Correlated Exposure.
- Leverage.
- Margin Requirements.
- Liquidity Risk.
- Concentration Risk.
- Asset Class Limits.
- Instrument Limits.
- Risk Budget Compliance.
- Scenario Analysis.

Risk Profile должен задаваться отдельно и быть формализованным.

Hard Risk Limits:
- проверяются детерминированным кодом;
- не могут быть изменены LLM;
- не могут обходиться ради привлекательного сигнала;
- применяются независимо от рекомендаций торговых агентов.

**Output:**
- `validated_portfolio`
- `risk_validation_report`
- `risk_limit_status`

## STAGE 16 — Production Packaging & Trading Deployment

**Цель:** подготовить проверенные модели и стратегии к использованию в торговой системе.

Содержание:
- Model Packaging.
- Model Versioning.
- Strategy Configuration.
- Signal Definitions.
- Input/Output Schemas.
- Dependency Management.
- Automated Tests.
- Model Registry.
- Production Status.
- Activation.
- Rollback.
- Monitoring Requirements.
- Agent Input Packages.

Интеграция двух торговых LLM:

**Signal LLM**
- получает production-ready модели и стратегии;
- сканирует universe;
- отбирает торговые возможности;
- возвращает BUY / SELL / NO SIGNAL;
- не определяет размер позиции.

**Sizing LLM**
- получает отобранные возможности;
- получает актуальное состояние портфеля;
- учитывает Risk Profile и portfolio constraints;
- определяет целевую экспозицию от нуля до верхнего лимита;
- не создаёт собственные alpha-сигналы.

Все реальные изменения позиций остаются под ручным подтверждением человека.

**Output:**
- `production_model_registry`
- `agent_input_packages`
- `production_configs`
- `deployment_report`

## STAGE 17 — Live Trading, Attribution & Agent Evolution

**Цель:** отслеживать реальную работу системы, оценивать качество решений и совершенствовать торговую логику и поведение агентов.

Содержание:

**Live Performance Monitoring**
- Live Strategy Performance.
- Portfolio Performance.
- Exposure Monitoring.
- Risk Monitoring.
- Drawdown Monitoring.
- Signal Monitoring.
- Strategy Degradation.

**Performance Attribution**
- Signal Attribution.
- Sizing Attribution.
- Strategy Attribution.
- Portfolio Attribution.
- Instrument Attribution.
- Regime Attribution.
- Transaction Cost Attribution.

**Agent Evaluation**
- Signal Selection Quality.
- Signal Direction Quality.
- False Positive Analysis.
- False Negative Analysis.
- Sizing Quality.
- Portfolio Allocation Quality.
- Rejected Opportunity Analysis.
- Human Approval/Rejection Analysis.
- Recommendation vs Actual Execution.
- Agent Consistency.

**Alpha Monitoring**
- Alpha Decay.
- Model Drift.
- Feature Drift.
- Regime Changes.
- Performance Degradation.
- Strategy Capacity.

**Agent Evolution**
- Journal Analysis.
- Behavioral Pattern Discovery.
- Error Classification.
- Learning Hypothesis Generation.
- Research Request Generation.
- Agent Configuration Improvement.
- Instruction Optimization.
- Threshold and Policy Revision.
- Shadow Testing.
- Controlled Promotion.

Meta-Agent совершенствует торговых агентов через версионирование инструкций, конфигураций, policies и thresholds.

Изменение весов LLM и fine-tuning не входят в базовый механизм улучшения.

Никакие изменения не должны автоматически попадать в ACTIVE без предусмотренной процедуры проверки и promotion.

**Output:**
- `agent_performance_report`
- `performance_attribution`
- `learning_hypotheses`
- `research_requests`
- `proposed_agent_updates`

---

## 8. Сквозная инфраструктура Pipeline

Следующие компоненты не являются дополнительными этапами. Они обслуживают все 17 этапов:

- Data Registry.
- Dataset Versioning.
- Instrument Master.
- Feature Registry.
- Method Registry.
- Experiment Tracking.
- Experiment Engine.
- Evaluation Framework.
- Model Registry.
- Strategy Registry.
- Artifact Storage.
- Configuration Management.
- Logging and Monitoring.
- Reproducibility Infrastructure.

## 9. Обязательные архитектурные принципы

1. Каждый этап имеет формальные входы и выходы.
2. Результаты исследований сохраняются как версионируемые артефакты.
3. Любой эксперимент можно воспроизвести.
4. Любое решение о продвижении модели имеет обоснование и критерии приёмки.
5. Никакая модель не попадает в production только из-за хорошего backtest.
6. Статистическая значимость не равна экономической эффективности.
7. Gross alpha не равен net alpha.
8. OOS и robustness validation обязательны.
9. Отрицательный исследовательский результат — полноценный результат.
10. LLM не заменяет детерминированные расчёты и контроль риска.
11. Signal и Sizing имеют строго разделённые зоны ответственности.
12. Ручное подтверждение реальных изменений позиций обязательно.

## 10. Требуемый результат проектирования

Не ограничивайся описанием этапов.

Нужно постепенно превратить эту спецификацию в реализуемую архитектуру:

- модульная структура Python-проекта;
- контракты данных;
- schemas;
- интерфейсы компонентов;
- pipeline orchestration;
- experiment tracking;
- artifact management;
- validation gates;
- model registry;
- production deployment;
- agent integration;
- monitoring and feedback loop.

Каждый этап должен быть реализуемым независимо, но интегрированным в общую систему.

Не начинай писать весь проект одним большим коммитом. Сначала исследуй существующую архитектуру и данные, затем составляй план реализации.

**Главный принцип: 17 этапов — единый исследовательский процесс от рыночных данных до эволюции торговых агентов. Сохраняй эту структуру и не смешивай её с архитектурой отдельных LLM.

---

# Architecture governance update — 2026-11-27

This update records the user's explicit replacement of the conversational multi-agent trading pilot. It is authoritative over any conflicting legacy references to Aggressive Trading, Signal LLM, Sizing LLM, or the previous three-agent conversational pilot above. The original 17 research and production stages remain unchanged.

## 1. Operating architecture

The project uses two distinct capital sleeves and three functional responsibilities:

1. **Model-driven trading sleeve — 50% strategic capital allocation.** Trading signals originate from validated predictive/research models. No Aggressive Trading LLM, Conservative Trading LLM, or conversational signal selector sits between the model output and portfolio review. A model is the signal source.
2. **Investment sleeve — 50% strategic capital allocation.** A separate Conservative Investment process remains active, led by ChatGPT under Meta-Agent governance. It uses business, sector, fundamental and valuation evidence and is not required to follow model signals.
3. **Meta-Agent / Portfolio Steward — ChatGPT.** Owns process oversight, model-evidence and trust tracking, model preference recommendations, portfolio sizing proposals, cross-sleeve capital oversight, and governance of the Research Agent and Investment Agent.

The 50/50 split is a strategic allocation between the two sleeves, not a requirement to keep either sleeve fully invested. If a sleeve has no justified opportunity or no eligible model, its capital may remain in cash. Do not force deployment to satisfy a target exposure.

## 2. Trading signal source and model lifecycle

- The research model produces the directional signal or forecast according to its own validated contract.
- ChatGPT does not invent or replace the model's BUY/SELL output. ChatGPT receives model outputs and evaluates their provenance, current validity, uncertainty, portfolio implications and sizing.
- Each output must identify the model and version, data/as-of timestamp, universe, target/horizon, signal/forecast, confidence or uncertainty representation, validity conditions and relevant research artifact.
- Research status is not production status. A promising experiment does not automatically become an eligible live signal source.
- Model activation, suspension, replacement and retirement require traceable evidence and an explicit user-approved promotion decision.
- No automatic broker integration, order submission or unattended changes to real positions are authorized. Real portfolio changes remain subject to user confirmation.

## 3. Model evidence and trust register

The Meta-Agent maintains a model register and a longitudinal evidence record. Trust is an evidence-based profile, not an arbitrary single scalar score.

For every model/version, record where applicable:
- research question, model family, version and owner;
- dataset and data snapshot, point-in-time rules, universe, target and horizon;
- training/validation/test or walk-forward protocol and temporal coverage;
- sample size, prediction coverage, missingness and benchmark/baseline definition;
- predictive quality, calibration and uncertainty metrics appropriate to the target;
- out-of-sample and walk-forward stability, subperiod and regime dependence;
- robustness, sensitivity, leakage checks and known failure modes;
- transaction-cost and implementation assumptions when economic evaluation is permitted;
- shadow/paper observations and actual live outcomes, kept distinct;
- current status, approval date, limitations and reason for status changes.

Model preference must be conditional on the task, horizon, universe, market conditions and available evidence. Do not rank models using one metric, one backtest, one short period or an invented weighted score. When several models exist, compare them on common data and protocols where possible, expose uncertainty and disagreement, and state where evidence is insufficient to prefer one. A model may be preferred for one task or regime and not another.

The Meta-Agent must not fabricate a model's track record or infer live reliability from code inspection or an in-sample result. Evidence labels must distinguish user-run, repository-verified, independently rerun, shadow and live observations.

## 4. Portfolio and sizing responsibility

The Meta-Agent is responsible for portfolio-level reasoning and sizing proposals across the two sleeves:
- preserve the strategic 50/50 split unless the user explicitly changes it;
- evaluate model-driven opportunities only from eligible model outputs and the current portfolio state;
- evaluate investment opportunities through the separate Investment Agent's documented business/fundamental case;
- account for concentration, correlation, liquidity, costs, uncertainty, model disagreement, capital availability and user-approved Risk Profile constraints;
- explain proposed weights, alternatives, abstention and changes from the previous allocation;
- keep unused sleeve capital in cash when evidence or constraints do not justify deployment.

No Risk Profile limit may be invented or silently changed. The Meta-Agent may propose allocations but does not execute trades. Numerical sizing is provisional when required portfolio state, constraints or cost assumptions are missing.

## 5. Research Agent governance

The Research Agent remains an active specialist responsible for research questions, hypotheses, experiment design, implementation, statistical analysis, model development and scientific conclusions. Its underlying LLM is not architecturally fixed; Qwen may be used, but the project should accumulate evidence about model quality rather than assume a permanent winner.

The Meta-Agent:
- monitors research progress, approved scope, artifact provenance, reproducibility, validation status and handoff quality;
- maintains model/version evidence and tracks downstream performance after promotion;
- reviews the Research Agent's process and updates its role instructions when recurring process errors are observed;
- may request clarification, replication or additional evidence;
- does not take over scientific ownership or silently rewrite research methods/results.

The Research Agent's own research journal remains the canonical chronological record of scientific research decisions and results. The Meta-Agent's project journal records project-level architecture, model governance, portfolio and process decisions. The user's personal journal remains separate and user-owned.

## 6. Investment Agent governance

The Conservative Investment Agent remains active as a separate investment-analysis process. It is governed by the Meta-Agent and has its own role instructions and journal under `llm_memory/meta_agent/`.

Its key process correction is sector-first screening before selecting individual companies. It must assess sector economics and the business mechanism first, then identify leaders for company-level verification. It must not manufacture opportunities or infer fundamental quality from price-only market diagnostics.

The Investment Agent does not generate model signals and does not control the model sleeve. Its recommendations feed the investment sleeve only.

## 7. Retired conversational roles

The following pilot roles are retired and are not active components:
- Aggressive Trading LLM;
- conversational Signal LLM;
- separate Sizing LLM;
- the former three-agent manual trading pilot and its shared operating protocol.

The former Conservative Investment role is retained as the Investment Agent, migrated into Meta-Agent memory. Historical journals and project decisions are preserved where useful; retired role files are removed from the active agent directory.

## 8. Operational cadence

The default workflow is:
1. Research Agent conducts research and returns reproducible model/evidence packages.
2. Meta-Agent reviews process quality, provenance, validation status and model-register implications.
3. Eligible model outputs are supplied to Meta-Agent for portfolio context and sizing proposals.
4. Investment Agent independently develops or updates the fundamental investment case for its sleeve.
5. Meta-Agent reviews both sleeves, maintains the 50/50 strategic capital split, and proposes portfolio actions or abstention.
6. User reviews and manually approves any real portfolio changes.
7. Actual outcomes and model versions are logged to update the evidence record and future model preferences.

The priority is to spend time on substantive research and model quality, not on maintaining a slow conversational agent chain.
