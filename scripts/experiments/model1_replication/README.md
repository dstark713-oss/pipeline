# model1 replication on pipeline PIT TOP50

Run from repository root:
\`\`\`powershell
python scripts/experiments/model1_replication/run_replication.py
\`\`\`
Use --skip-backtest to run only WF/classification metrics.

The script reads data/processed/moex_daily_adjusted.sqlite (adjusted_daily_bars) and data/processed/top50/top50_panel.parquet read-only. Outputs go to data/interim/model1_replication/ and are not committed.

Copied from model1: feature formulas/windows, H=5 Triple Barrier (TP=1.5 sigma, SL=1.0 sigma, volatility window 20), two CatBoost classifiers (500 iterations, depth 6, learning rate 0.05, L2 3, min_data_in_leaf 20, seed 42), isotonic calibration, expanding WF (3-year initial train, 6-month retrain/test, 10 calendar-day purge), score P(TP)*(1-P(SL)), N grid 4..8, correlation window 20/threshold 0.8, breadth EMA20, costs 3+3 bps.

PIT adaptation: feature warmup uses full observed security history; rows enter the model only when the security belongs to PIT TOP50 on signal date and bar_available=1. No forward-fill. OHLC selects one complete board row, TQBR first and EQBR fallback; adjusted volume/value are summed across boards. Breadth uses current PIT TOP50 members.

Important inherited limitations are preserved and recorded: isotonic calibration is fit on predictions from the same training sample used to fit the model; N selection optimizes mean predicted score rather than realized performance; breakout rolling high/low includes current bar. model1's market.py is not called by its feature pipeline, so it is not added here.

The inherited portfolio backtest holds Open(t+1)->Open(t+2), one session, while the model labels use a five-session Triple Barrier horizon. Sharpe/CAGR/MDD are therefore diagnostic only and not an economically aligned validation of the H=5 target.

No local dataset execution is performed by the authoring step. Run the script locally and share outputs for analysis.