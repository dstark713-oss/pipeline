# EDA2 — исследовательские блоки

Скрипты запускаются из корня репозитория. Все блоки используют существующую панель
data/processed/top50/top50_panel.parquet, если явно не передан другой путь.
Они не обращаются к MOEX ISS, не запускают сборку датасета и не изменяют SQLite.

## Блок 1. Геометрия распределения доходностей

Запуск:

    python scripts/experiments/eda2/01_return_distribution.py

Исследуются:
- pooled-распределение дневных логарифмических доходностей;
- индивидуальные распределения бумаг и оценки с равным весом каждой бумаги;
- квантили, асимметрия, эксцесс, MAD и частоты экстремальных движений;
- годовые изменения формы распределений;
- поперечные статистики доходностей по датам и их временное распределение.

Машинные артефакты:
- data/interim/eda2/block_01/security_distribution.csv
- data/interim/eda2/block_01/yearly_distribution.csv
- data/interim/eda2/block_01/daily_cross_sectional_distribution.csv
- data/interim/eda2/block_01/run_metadata.json

Агрегаты для анализа Research Agent:
- docs/research/eda2/results/block_01/overall_distribution_summary.csv
- docs/research/eda2/results/block_01/security_heterogeneity_summary.csv
- docs/research/eda2/results/block_01/yearly_distribution_summary.csv
- docs/research/eda2/results/block_01/cross_sectional_time_summary.csv
- docs/research/eda2/results/block_01/EDA2_BLOCK_01_REPORT.md

Методологические правила:
- Доходность считается только между соседними сессиями панели.
- На обеих соседних сессиях должны быть положительный adjusted close и bar_available=1.
- Пропуски не заполняются, доходности через пропущенные сессии не рассчитываются.
- Pooled-оценки взвешивают наблюдения «бумага-дата»; equal-security оценки сначала считают статистику каждой бумаги, затем усредняют бумаги с равным весом.
- MAD — немасштабированная медиана абсолютных отклонений от медианы.
- Эксцесс использует определение Fisher.
- Блок описательный: без тестов гипотез, IC, отбора признаков, моделей, прогнозов, торговых правил и портфельных метрик.

## Блок 3. Межбумажная зависимость и совместное движение

Запуск:

    python scripts/experiments/eda2/03_cross_sectional_dependence.py

Блок 3 завершён. Его методика и результаты описаны в
docs/research/eda2/results/block_03/EDA2_BLOCK_03_REPORT.md.
