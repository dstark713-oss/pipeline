# Conservative regime hypothesis checks

One-use diagnostic for the conservative investment pilot.

Hypothesis:
"The recent Russian equity-market rebound does not yet establish a broad, durable improvement in the fundamental regime."

## Scope

The script tests observable market breadth and return-contribution concentration using the existing point-in-time TOP50 adjusted-price panel. It does **not** claim that this is the IMOEX or a sector-neutral market portfolio.

It deliberately separates:
- **Confirmation evidence:** narrow breadth, weak median/equal-weight return relative to concentrated positive-return contributions.
- **Potential falsification evidence:** broad positive breadth and sustained equal-weight participation in a user-selected recent subperiod.
- **Fundamentals:** manually curated narrative/company evidence only. There is no automated accounting-data layer.
- **External drivers:** optional user-supplied daily market-context CSV. Correlations are descriptive, not causal.

No BUY/SELL/target weight is produced.

## Input data

Default panel:
`data/processed/top50/top50_panel.parquet`

Required columns:
- `tradedate`
- `secid`
- `adjusted_close`
- `bar_available`

Returns are calculated only when the current and previous observations are valid and correspond to adjacent panel sessions. No forward-fill, no bridging gaps.

## Run

From repository root:

```powershell
python scripts/one_use/conservative_regime_check/check_regime_hypothesis.py
```

Optional recent window and manual market context:

```powershell
python scripts/one_use/conservative_regime_check/check_regime_hypothesis.py --recent-start 2026-07-01 --market-context data/interim/one_use/regime_check/market_context_template.csv --fundamentals data/interim/one_use/regime_check/manual_fundamental_evidence_template.csv
```

The script creates templates if absent. Replace the template CSV contents with sourced observations before passing them as inputs. Market returns must be decimal returns (e.g. 0.012 = +1.2%). Keep the meaning/sign convention of USDRUB return explicit: positive means USD/RUB rose (ruble weakened).

## Outputs

Written locally to `data/interim/one_use/regime_check/`:
- `daily_regime_metrics.csv`
- `period_summary.csv`
- `security_return_summary.csv`
- `manual_fundamental_evidence_template.csv`
- `market_context_template.csv`
- `run_metadata.json`

Generated outputs and input datasets must not be committed to Git.

## Interpretation guardrails

- Breadth above 50% is a descriptive majority threshold, not a statistically validated trading threshold.
- Top-k contribution shares and positive-return HHI measure concentration among positive daily returns, not index-weight concentration.
- TOP50 membership changes through time. This is a point-in-time universe, but the equal-weight return series is not a buy-and-hold portfolio.
- The script does not identify sector concentration because a verified sector mapping is not currently part of this input contract.
- Fundamental conclusions require manual review of company reports and source-linked evidence. Empty template means **fundamental check not performed**, not "no fundamental improvement".
- A correlation with IMOEX, Brent or USD/RUB does not prove that the driver caused market returns.
- Results are diagnostics for the approved hypothesis, not a standalone investment signal.
