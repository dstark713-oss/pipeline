# Meta-Agent Working Context

Last updated: 2026-11-23

## Source of truth and operating boundaries

- Main project repository: \`dstark713-oss/pipeline\`.
- GitHub is the source of truth for committed code and project context.
- The user runs Python locally in VS Code and supplies execution output for diagnosis.
- Never claim local runtime validation unless the user has supplied the result.
- The user explicitly authorizes code changes when they say to implement/build/commit a requested tool or script. Do not make unrelated code changes.
- Prefer complete runnable Python files over patch instructions.
- Every Python file must begin with comments containing its folder path and filename.
- Do not commit raw data, SQLite databases, Parquet datasets, CSV calculation outputs, logs, caches, or temporary files.
- Preserve instrument identity: SECIDs are distinct instruments. Do not merge SECIDs by issuer, ISIN, name, or economic relationship unless the user explicitly defines a specific deduplication rule for a specific task.

## Research and scanner objective

The project is building an interpretable instrument-state information layer for a downstream agent.

The screener is not a classical trading strategy, signal-to-weight optimizer, portfolio constructor, or execution engine. Research asks whether a primitive contains real, robust, interpretable information. It does not optimize CAGR or reject a primitive merely because a portfolio experiment has an unattractive return metric.

The downstream agent decides what to do with scanner information in the context of its own mandate and portfolio. The screener must not issue automatic buy/sell/hold instructions or target weights.

## Approved instrument-level core primitives

1. \`drawdown_60\`
   - Close / rolling 60-session maximum close - 1.
   - Higher values mean closer to the 60-session high.
2. \`zscore_sma20_20\`
   - (Close - SMA20) / rolling 20-session sample standard deviation of the residual (Close - SMA20).
   - Positive means above SMA20; negative means below.
3. \`realized_vol_60\`
   - 60-session sample standard deviation of daily close returns multiplied by sqrt(252).
   - Backward-looking annualized realized volatility, a state/risk descriptor rather than a return forecast.

Breadth is a separate market-level state family. Do not mix it into per-instrument rankings or treat it as a fourth instrument-level primitive.

## Screener implementation

- Main tool: \`scripts/tools/01_primitive_screener.py\`.
- User-facing option: \`--inspect\`, which prompts for one or more SECIDs separated by spaces.
- Current snapshot source: latest date in \`data/processed/top50/top50_panel.parquet\`.
- Primitive values: \`data/interim/primitive_research/primitive_features.parquet\`.
- Output: \`data/interim/screener/latest_primitive_snapshot.csv\`.
- One row per current PIT TOP50 member; retains members with no bar and reports missingness explicitly.
- Console prints TOP 15 separately for each primitive, sorted descending. For drawdown_60, descending means closest to the 60-session high.
- Ticker inspection reports snapshot date, PIT liquidity rank, bar availability, primitive values, cross-sectional ranks, percentiles, and missing-value status.
- No composite score, strategy logic, weights, or automatic action.
- Screener documentation: \`docs/tools/01_primitive_screener.md\`.

## Important distinctions

- \`panel_rank\` is the PIT TOP50 turnover/liquidity rank, not a primitive rank.
- Primitive ranks are current cross-sectional descriptions among valid values only.
- Missing data is not zero and is not a neutral signal.
- The screener does not merge SECIDs by issuer or ISIN.
- Breadth remains a separate market-level context layer.
- The snapshot date is the latest panel date, not necessarily today's calendar date.
- The screener reads prepared feature data; it does not rebuild features or mutate source datasets.

## Recent methodological correction

A previous analysis drifted into treating a portfolio application experiment as a trading strategy and overemphasized CAGR/Sharpe/MDD. That was a framing error.

For future primitive work, focus on:
- whether an observed effect is real;
- whether it is an artifact of data, leakage, sample construction, or calculation;
- whether it is stable across time and market regimes;
- whether it adds distinct information;
- how the downstream agent may use the information.

Portfolio metrics are not the research objective and must not become the default acceptance criteria.
