# model1 daily TOP50 scoring tool

Run from the repository root:

```powershell
python scripts/tools/02_model1_daily_scores.py
```

The tool:
- Reads the latest date and all 50 securities from `data/processed/top50/top50_panel.parquet`.
- Reuses the replicated model1 feature definitions, Triple Barrier labels, CatBoost parameters and PIT training sample.
- Retrains the TP and SL CatBoost classifiers from scratch on every run, using all eligible historical rows available by the latest panel date.
- Excludes training rows whose complete five-session label horizon is not yet observable.
- Uses raw model outputs. No isotonic calibration is applied.
- Writes exactly 50 rows to:
  - `data/interim/model1_daily_scores/model1_scores_YYYYMMDD.csv`
  - `data/interim/model1_daily_scores/model1_scores_latest.csv`

The CSV keeps every security in the latest PIT TOP50 panel. Securities that cannot be scored retain empty score fields and an explanatory `status`; this includes rows with unavailable bars and securities excluded by the replicated model's inherited exclusion list.

Columns:
- `tradedate`: latest panel signal date.
- `secid`, `ranking_asof_date`, `bar_available`: PIT panel identity and availability.
- `tp_raw_score`, `sl_raw_score`: uncalibrated CatBoost outputs; do not interpret as calibrated probabilities.
- `composite_score`: inherited model1 combination `tp_raw_score * (1 - sl_raw_score)`; a ranking score, not a probability.
- `rank`: descending rank among successfully scored securities.
- `status`: scoring eligibility/result.

The tool is an information provider for the agent, not a trading or portfolio optimizer. It does not run the legacy backtest or use its N-selection logic.

All generated files remain under `data/interim/` and should not be committed.
