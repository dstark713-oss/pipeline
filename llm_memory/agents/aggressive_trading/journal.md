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