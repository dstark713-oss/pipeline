# Aggressive Agent Journal — 2026-11-26

## Context
- as-of: 2026-11-26
- panel: data/processed/top50/top50_panel.parquet
  - 203453 rows, 214 symbols, 2005-01-11 → 2026-11-26
  - bar_available: 1 = 199219, 0 = 4234
- market context 26.11.2026: MOEX ~2336 (-0.7%), near 1.5-month lows,
  key rate 14.00%, USD/RUB ~82.13, weak/range-bound regime
- horizons: 1d (H1, H3), 5d (H2)
- costs: 7.5 bps/side, 15 bps round-trip
- portfolio: 100% cash
- previous decision: not supplied

## Hypotheses tested

### H1: 1d momentum continuation (ret_1d → fwd_1)
- mean IC = +0.0050, std = 0.2423
- negative control IC = +0.0007
- 49.55% of dates IC < 0
- top10% dates = 887% of total IC (sign flipping)
- LS after 15 bps: gross +0.174%, net +0.024%, hit 53.81%, std 2.23%
- by year: 13/22 negative, including 2023-2025
- **VERDICT: does not pass economic significance**

### H2: 5d cross-sectional momentum (ret_5d → fwd_5)
- mean IC = +0.0124, std = 0.2456
- negative control IC = +0.0005
- top10% dates = 358% of total IC
- LS after 15 bps: gross +0.286%, net +0.136%, hit 53.19%, std 5.17%
- by year: range -6.07% (2007) to +12.78% (2006), unstable
- **VERDICT: does not pass economic significance (noise-dominated)**

### H3: 1d mean-reversion after oversold (ret_1d < -2% → fwd_1)
- n = 24675, mean fwd_1 = -0.0973%, hit_rate = 49.63%
- baseline mean fwd_1 = +0.0580%
- effect direction OPPOSITE to hypothesis (continued weakness, not rebound)
- by year: 13/22 negative, including 2022, 2024, 2026
- net after 15 bps: ~0% (effect ~15.5 bps, costs 15 bps)
- **VERDICT: falsified as rebound hypothesis; not actionable as SELL either**

## Decision
- **NO SIGNAL**
- Reason: all three tested hypotheses fail economic significance after 15 bps round-trip costs;
  market context (weak, high rate, no trend) is consistent with this failure
- Portfolio: 100% cash, no position risk
- Invalidation: a hypothesis with different mechanism, different horizon, or different data
  showing positive net EV after costs

## Correction log
- 2026-11-26 (early): initial hypotheses built without reading market context or panel.
  Violated OPERATING_PROTOCOL §2 (CONTEXT → HYPOTHESIS → CHECK).
- 2026-11-26 (corrected): read panel + market context, rebuilt hypotheses from state,
  ran deterministic checks A/B/H3, interpreted results.
- Lesson: hypothesis must originate from CONTEXT, not from strategy template.

## Missing inputs / next required check
- Previous agent decision (for "Reason for change" block) — not supplied
- If continuing: alternative mechanism hypothesis (event-driven, fundamental cross-section,
  seasonality) — requires data beyond OHLCV

---

# Aggressive Agent Journal — Name-Level Handoff — 2026-11-27

## Operating correction from user
- This workflow is a **pipeline**, not open-ended research.
- Completed stages are closed. Do not invent extra validation rounds or reopen methodology after the agreed checks are complete.
- One iteration per stage. The agent owns the method; the user runs the local script and pushes the result.
- Current sequence: market snapshot → hypotheses → confirmation → falsification → name-level signal packet → handoff to Sizing Agent.
- Aggressive role in this workflow identifies short-horizon Long/Short candidates (approximately 3–20 sessions) and explains evidence. It does **not** size positions, issue target weights, or make portfolio-allocation decisions.
- Once the name packet is read, deliver names or explicitly no names, then stop. Sizing Agent owns position sizing and implementation checks.

## Completed name-level signal packet
- Snapshot date: 2026-11-26.
- PIT TOP50 universe: 50; current bars available: 50; eligible after data/liquidity filters: 45.
- Long candidates before cap: 13; final Long list capped at 10.
- Short candidates before cap: 4; all 4 passed the strict candidate filter.
- Intended horizon: 10–20 trading sessions.
- Filters: current adjusted close and complete core features; positive current traded value; turnover / 20D median at least 0.50.
- No sector labels, news assumptions, or unsupported catalysts were added.

## Final handoff: LONG — PRIMARY evidence
Selection rule: positive RS20 and top-quintile RS20 within the same RS5 quintile. This operationalizes the surviving incremental-RS20 falsification result while reducing selection driven by the shorter RS5 move.

| Rank | Ticker | RS20 | RS5 | Return 20D | Vol20 annualized | Turnover / median |
|---:|---|---:|---:|---:|---:|---:|
| 1 | CNRU | +25.90% | -0.80% | +21.24% | 64.60% | 1.06x |
| 2 | HYDR | +10.16% | -5.30% | +5.50% | 56.36% | 0.81x |
| 3 | SVCB | +7.16% | +1.70% | +2.50% | 35.19% | 0.55x |
| 4 | T | +7.04% | +0.78% | +2.38% | 23.11% | 0.68x |
| 5 | SMLT | +12.66% | +12.71% | +8.00% | 107.80% | 1.21x |
| 6 | DOMRF | +6.83% | +0.93% | +2.17% | 15.09% | 0.87x |
| 7 | MTSS | +1.80% | -2.36% | -2.87% | 17.44% | 0.82x |
| 8 | PHOR | +1.16% | +0.78% | -3.50% | 20.40% | 0.74x |
| 9 | VKCO | +10.46% | +5.43% | +5.79% | 94.59% | 0.54x |
| 10 | RTKM | +4.76% | -1.68% | +0.09% | 38.51% | 0.65x |

## Final handoff: SHORT — CONDITIONAL evidence
Selection rule: RS5 and RS20 both negative and both in the cross-sectional bottom quintile. This is intentionally stricter because persistent weakness (F3) was regime-dependent and borderline after multiple-testing adjustment.

| Rank | Ticker | RS20 | RS5 | Return 20D | Vol20 annualized | Turnover / median |
|---:|---|---:|---:|---:|---:|---:|
| 1 | RNFT | -14.36% | -5.62% | -19.02% | 44.39% | 1.78x |
| 2 | FEES | -7.38% | -5.93% | -12.05% | 39.35% | 1.16x |
| 3 | SGZH | -6.75% | -3.70% | -11.41% | 72.64% | 0.59x |
| 4 | GAZP | -5.85% | -4.38% | -10.52% | 34.79% | 0.68x |

## Evidence hierarchy and interpretation
- F1 (incremental RS20) survived falsification: within the same RS5 quintile, higher RS20 retained additional future relative-return information; the effect grew across 3/5/10/20-session horizons and was strongest at longer horizons.
- F2 (aligned positive 5D and 20D absolute returns) did not add incremental explanatory value. Do not create an alignment score.
- F3 (persistent weakness) was directionally negative but regime-dependent and borderline after multiple-testing adjustment. Short candidates remain conditional, not equivalent in confidence to Long.
- F4 (impulse concentration) was not supported. Close it; do not use concentration as a selection feature.
- Volatility was not supported as an explanation for the cross-sectional momentum effect. Volatility remains descriptive risk context for Sizing, not a directional alpha signal.
- Some Long candidates have negative absolute 20D returns (MTSS, PHOR) or high realized volatility (notably SMLT, VKCO). This is not a contradiction in the selection rule: RS is relative to the equal-weight PIT TOP50 benchmark. Sizing must inspect absolute-price behavior and risk context rather than treating relative strength as a guarantee of positive absolute return.
- No catalysts or news explanations were inferred.

## Handoff boundary
- Send Long list as primary candidate set to Sizing Agent.
- Send Short list as conditional candidates only. Sizing Agent independently checks short permission, borrow availability, instrument/venue constraints, portfolio risk and risk budget; reject any unsupported short.
- This journal contains no target weights, order instructions, or sizing recommendations.
- After this packet, Aggressive stage is complete. Do not add a new research stage unless the user explicitly reopens the process.

## Artifact availability note
- The report was fetched successfully from `docs/aggressive_name_signals_report.md`.
- The expected CSV path `data/interim/aggressive_name_signals/name_level_signals.csv` returned GitHub 404 and was not independently readable from the repository. The final ticker list and metrics above are transcribed from the committed Markdown report. Do not claim CSV was verified or committed.
