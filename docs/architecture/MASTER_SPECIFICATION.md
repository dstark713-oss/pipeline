# QUANT RESEARCH PIPELINE — MASTER SPECIFICATION

> Canonical source transferred into `dstark713-oss/pipeline/docs/architecture/` on 2026-11-26. The original 17-stage specification is preserved below; the Architecture Governance Addendum records the subsequently approved multi-agent architecture without altering the stage catalog.

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

**Цель:** формировать экономически и статистически обоснованные исследовательские гипотезы.

Направления:
- Momentum.
- Trend Following.
- Mean Reversion.
- Carry.
- Futures Term Structure.
- Seasonality.
- Volatility Premium.
- Cross-Asset Relationships.
- Relative Value.
- Positioning Effects.
- Macro Relationships.
- Regime-Dependent Effects.
- Liquidity Effects.

Для каждой гипотезы определить:
- экономический механизм;
- предполагаемое поведение рынка;
- предполагаемое направление эффекта;
- инструменты и классы активов;
- временной горизонт;
- необходимые данные;
- предполагаемые признаки;
- потенциальные confounding factors;
- условия применимости;
- критерии подтверждения;
- критерии опровержения.

Гипотеза не должна приниматься только потому, что она показывает хорошую историческую доходность.

**Output:**
- `research_hypothesis`
- `hypothesis_registry`
- `research_priority`

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