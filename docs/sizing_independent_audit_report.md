# Sizing independent audit — first iteration

- Panel: C:\Users\Danil\Desktop\pipeline\data\processed\top50\top50_panel.parquet
- Data: 2005-01-11 to 2026-11-26, 5,491 sessions, 214 tickers.
- PIT guard: ranking_asof_date strictly precedes tradedate: PASS.
- Cost assumption: 15.0 bps round-trip, charged once per completed holding period.
- Historical signal tests use daily PIT TOP50 membership; future returns require the exact h-session endpoint. Missing bars are not forward-filled.

## Aggressive Trading — falsification

 side  horizon  signals  signal_dates  mean_net  median_net  hit_rate_net  mean_excess  positive_year_fraction  worst_year_mean  best_year_mean  mean_names_per_date
 LONG       10    45160          5329    0.0041     -0.0004        0.4964       0.0023                  0.5455          -0.0259          0.0417               8.4744
SHORT       10    13708          4726   -0.0022      0.0013        0.5090      -0.0018                  0.3182          -0.0234          0.0588               2.9006
 LONG       20    44230          5297    0.0098      0.0025        0.5124       0.0042                  0.5909          -0.0373          0.0847               8.3500
SHORT       20    13216          4673   -0.0044     -0.0017        0.4910      -0.0049                  0.3636          -0.0466          0.0704               2.8282

Latest snapshot rebuilt from panel: 12 Long / 4 Short. Overlap with reported 26-Nov list: Long 8/10; Short 3/4.
A low overlap means the committed name packet is not reproducible from this independent reconstruction; inspect benchmark/feature definitions before sizing.
Long results also report excess return versus the same-date PIT equal-weight cross-section; Short results are evaluated on absolute short P&L. Every intervening session bar is required for forward outcomes.
Historical cohort means are diagnostics, not a fully executable portfolio backtest: signals overlap and no turnover/borrow/slippage model beyond the stated round-trip cost is included.

## Conservative Investment — falsification

  period      start        end  sessions  breadth_mean  breadth_gt50  ew_return_mean  median_return_mean  top5_positive_share_mean
    FULL 2005-01-12 2026-11-26      5484        0.4822        0.4539          0.0003             -0.0010                    0.6895
LAST_120 2026-06-17 2026-11-26       120        0.4710        0.4750         -0.0007             -0.0020                    0.6175
 LAST_60 2026-09-09 2026-11-26        60        0.4799        0.5333          0.0002             -0.0011                    0.6067
 LAST_20 2026-11-05 2026-11-26        20        0.4469        0.5500         -0.0023             -0.0031                    0.6168
 2026_Q4 2026-10-01 2026-11-26        44        0.5080        0.5909          0.0013             -0.0003                    0.5768

Sector/fundamental columns present in panel: NONE.
The panel can challenge broad-market participation claims but cannot validate sector economics, company fundamentals, valuation, or a positive BUY case.
Therefore the current 100% cash posture is consistent with absence of verified fundamental evidence, but is NOT proven optimal by this price-only audit.

## Decision gate

- Do not size either handoff until the user returns this script's output and the latest actual portfolio / risk constraints are supplied.
- Aggressive Longs are candidate signals, not independently validated allocations. Shorts remain conditional and require explicit permission plus borrow/implementation evidence.
- Conservative has no sector/company BUY thesis in its journal; no capital deployment is justified by breadth diagnostics alone.
- Mandate remains 50% Aggressive sleeve / 50% Conservative sleeve. This audit does not alter that split.

## Output files

- aggressive_historical_falsification.csv
- conservative_regime_recheck.csv
- latest_packet_reconciliation.csv
