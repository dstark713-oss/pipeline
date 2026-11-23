# Market Breadth Research

Independent research block for evaluating whether market breadth deserves to become a fourth scanner layer alongside the three selected instrument-level primitives.

## Run

From the repository root:

\`\`\`bash
python scripts/experiments/primitives/breadth/run_breadth_research.py
\`\`\`

The launcher reuses the established loader, board aggregation, point-in-time TOP50 membership, adjusted-price history, and forward-return definitions from:

\`scripts/experiments/primitives/01_research_report.py\`

This avoids maintaining a second implementation of the same data rules.

## Research design

- Breadth is calculated on each signal date from the PIT TOP50 cohort.
- SMA breadth is the share of valid signal-date members above SMA20, SMA50, or SMA200.
- \`breadth_change_5\` and \`breadth_change_20\` are changes in SMA20 breadth over 5 and 20 market sessions.
- Forward outcomes use the same signal-date cohort, whether or not a member remains in TOP50 later.
- Forward return is \`Close[T+H] / Open[T+1] - 1\`, for H = 5, 10, 20.
- The analysis measures future mean return, median return, and the share of members with positive future returns.
- Correlations use Newey-West/HAC tests with lags up to H-1 and Benjamini-Hochberg q-values.
- Period stability, 252-session rolling correlations, quantile analysis, and a nonparametric double-sort by past member returns are included.
- No regression, fitted model, strategy backtest, price forward-fill, or raw-data mutation is performed.

## Outputs

Written to \`data/interim/primitive_research/breadth/\`:

- \`breadth_daily.csv\`
- \`breadth_correlation_summary.csv\`
- \`breadth_period_stability.csv\`
- \`breadth_quantile_summary.csv\`
- \`breadth_double_sort.csv\`
- \`breadth_rolling_summary.csv\`
- \`breadth_report.md\`
- \`breadth_metadata.json\`

The output directory is local research data and must not be committed.
