# Next Steps and Open Questions

Last updated: 2026-11-23

## Immediate research priority

Continue the primitive experiment, not the production screener.

The first report is exploratory. Do not select primitives from mean IC ranking alone.

### Diagnostic sequence

1. Formula/sign audit of leading features:
   - drawdown_60 and drawdown_20 are close / rolling-high - 1; less negative means closer to the high.
   - sma50_sma200 is SMA50 / SMA200 - 1.
   - zscore_sma20_20 is (close - SMA20) / rolling standard deviation of the residual.
   - realized_vol_20/60 are annualized rolling standard deviations of close-to-close returns.
   - rs_rank_20/60 rank past returns within the date's PIT TOP50; rank 1 is strongest.
2. Decile analysis for horizons 5/10/20; inspect monotonicity, spread, tails, and stability.
3. Correlation matrix across primitives; identify redundant features and distinct information groups.
4. Period stability for 2005-2012, 2013-2019, 2020+.
5. Coverage and missingness analysis, including whether low-coverage tickers/dates bias the cross-section.
6. Review breadth as a separate market-level family.
7. Recommend a compact, interpretable, orthogonal pack for user approval.

Likely candidate families, still provisional:
- Trend / price location: drawdown_60, SMA50/SMA200, z-score vs SMA20.
- Relative strength: RS rank, but resolve early-period instability.
- Risk: realized volatility.
- Participation: positive-turnover share.
- Market state: short-term breadth change.

Do not assume every family must be represented. Retain only what demonstrates robust incremental information.

## Data pipeline priorities

- Do not rebuild completed universe/raw/audit/adjustment stages without a concrete defect.
- Verify that the current refresh script works locally before relying on it.
- Resolve refresh edge cases: delayed publication after an empty response; cutoff based on calendar yesterday; coverage of SECID/board pairs absent from raw history.
- Keep historical and daily TOP50 ranking implementations identical.
- Keep raw immutable and derived outputs rebuildable.
- No production launcher for the screener until research selection is complete.

## Later production screener (deferred)

When the primitive pack is approved:
- Build a simple launch point under the agreed production tools location (currently discussed as `tools/01_screener`; do not create it yet).
- Produce a latest-date snapshot of each current PIT TOP50 instrument.
- Include primitive values, clear definitions, units/sign conventions, missingness/coverage status, and an agent-facing description.
- The screener describes states; it does not generate trades, allocate weights, or replace portfolio logic.
- Keep the output deterministic and reproducible.

## Long-term direction

The broader project direction discussed with the user is an autonomous research/agent environment that can progressively research, create, and evaluate tools while learning from a live market. A possible 6-12 month horizon was discussed for a more capable learning/RL loop. This is a long-term direction, not the current implementation status or a promise of autonomous live trading.

The immediate project remains much narrower: reliable data → interpretable primitives → robust diagnostics → user-approved state screener.
