# Pipeline

Research and data infrastructure for systematic analysis of the Russian equity market, built on MOEX ISS data.

The repository separates market-data collection, dataset construction, research experiments, and agent context. The goal is reproducible data and research workflows, not a monolithic trading bot.

## Project scope

- Discover and maintain the historical securities universe.
- Collect historical and incremental daily market data from MOEX ISS.
- Preserve raw source data locally and build downstream adjusted datasets and point-in-time panels.
- Run isolated, reproducible statistical and machine-learning experiments.
- Maintain concise research-agent context under `llm_memory/`.

## Repository layout

```text
pipeline/
├── data/                         # local datasets and databases; never commit
├── scripts/
│   ├── dataset/                  # raw collection, refresh, and dataset building
│   ├── tools/                    # command-line entry points and utilities
│   └── experiments/              # isolated research experiments
├── docs/                         # project documentation
└── llm_memory/                   # concise context for research/work agents
```

The exact contents of these directories evolve. Experiment outputs, downloaded data, SQLite databases, Parquet files, logs, caches, and other generated artifacts belong in local data/output locations and must remain out of Git.

## Data principles

- Keep source collection, transformations, and analytical panels as separate stages.
- Retain source identifiers such as SECID and BOARDID, along with trading dates and source metadata.
- Make collection and refresh operations resumable and safe to rerun.
- Treat MOEX as the source of truth for downloaded observations. If MOEX revises an existing candle, the refresh process should update the local raw observation rather than fail solely because the value changed.
- Keep refresh behavior explicit and deterministic; do not silently introduce forward-filling or synthetic observations.
- Preserve enough metadata and logs to diagnose collection coverage and failures.
- Never commit raw databases, Parquet datasets, API responses/caches, or generated experiment outputs.

## Research tracks

### ML Direction Prediction

A feature-research program using daily OHLCV data as a practical domain for developing statistical learning and time-series analysis skills.

Current task definition:
- Historical point-in-time TOP50 Russian equities.
- Five-session prediction horizon.
- Binary target: adjusted Close at signal date (t) versus adjusted Close at (t+5).
- Features use information available no later than the close of (t).
- Final model evaluation is planned with expanding-window walk-forward validation, an initial three-year training window, monthly retraining, and purging of training labels that extend beyond the training cutoff.

Feature research is conducted one family at a time. Individual IC is a diagnostic, not an automatic feature-selection rule. Feature coverage, temporal stability, redundancy, and conditional information matter as well.

The first completed exploratory feature experiment is Rolling Statistical Moments (rolling mean, variance, skewness, and Fisher excess kurtosis over 20/60/120/240-session windows). Its initial report is preliminary: the HAC inference needs a calendar-spacing correction because dates with insufficient cross-sectional observations were dropped before the time-series standard-error calculation. The experiment also surfaced unexpectedly low skewness coverage that requires diagnosis. Do not treat its initial p-values or feature rankings as final conclusions.

Research-agent context and detailed specifications are maintained in:
`llm_memory/research_agent/06_ML_DIRECTION_FEATURE_RESEARCH.md`.

## Running locally

Run commands from the repository root using the project's configured Python environment. For example, the daily refresh entry point is:

```powershell
python scripts/tools/00_refresh_ds.py
```

Individual experiment READMEs document their own commands, inputs, parameters, and outputs.

## Reproducibility and changes

- Record experiment assumptions before execution.
- Keep feature definitions, target construction, universe rules, and evaluation protocols explicit.
- Do not use portfolio metrics for iterative feature/model selection in the ML Direction Prediction research track. A single decisive portfolio evaluation is reserved for an approved final model.
- Do not claim a local experiment or refresh succeeded unless its execution output confirms it.
