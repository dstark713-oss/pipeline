# Aggressive Agent: Name-Level Signal Packet

- Snapshot date: **2026-11-26**
- PIT TOP50 universe rows: **50**
- Current bars available: **50**
- Eligible after data/liquidity filters: **45**
- Long candidates before cap: **13**
- Short candidates before cap: **4**
- Intended horizon: **10–20 trading sessions**
- This packet provides directions and evidence, not position sizes.

## Selection logic

- Long: positive RS20 and top-quintile RS20 within the same RS5 quintile. This operationalizes the surviving F1 result while controlling for the shorter RS5 stratum.
- Short: negative RS5 and RS20, both in their cross-sectional bottom quintiles. This is conditional because F3 was regime-dependent and borderline after multiple-testing adjustment.
- Both sides require a current adjusted close, complete core features, positive current traded value, and turnover/current 20D-median ratio at least **0.50**.
- Maximum **10** names per side. No parameter fitting or threshold optimization.
- No sector labels, news assumptions, or unsupported catalysts are added.

## Long candidates

| Rank | Ticker | RS20 | RS5 | Return 20D | Vol20 ann. | Turnover / median |
|---:|---|---:|---:|---:|---:|---:|
| 1 | **CNRU** | 25.90% | -0.80% | 21.24% | 64.60% | 1.06x |
| 2 | **HYDR** | 10.16% | -5.30% | 5.50% | 56.36% | 0.81x |
| 3 | **SVCB** | 7.16% | 1.70% | 2.50% | 35.19% | 0.55x |
| 4 | **T** | 7.04% | 0.78% | 2.38% | 23.11% | 0.68x |
| 5 | **SMLT** | 12.66% | 12.71% | 8.00% | 107.80% | 1.21x |
| 6 | **DOMRF** | 6.83% | 0.93% | 2.17% | 15.09% | 0.87x |
| 7 | **MTSS** | 1.80% | -2.36% | -2.87% | 17.44% | 0.82x |
| 8 | **PHOR** | 1.16% | 0.78% | -3.50% | 20.40% | 0.74x |
| 9 | **VKCO** | 10.46% | 5.43% | 5.79% | 94.59% | 0.54x |
| 10 | **RTKM** | 4.76% | -1.68% | 0.09% | 38.51% | 0.65x |

## Short candidates

| Rank | Ticker | RS20 | RS5 | Return 20D | Vol20 ann. | Turnover / median |
|---:|---|---:|---:|---:|---:|---:|
| 1 | **RNFT** | -14.36% | -5.62% | -19.02% | 44.39% | 1.78x |
| 2 | **FEES** | -7.38% | -5.93% | -12.05% | 39.35% | 1.16x |
| 3 | **SGZH** | -6.75% | -3.70% | -11.41% | 72.64% | 0.59x |
| 4 | **GAZP** | -5.85% | -4.38% | -10.52% | 34.79% | 0.68x |

## Handoff notes for Sizing Agent

- LONG candidates are the primary evidence-backed side.
- SHORT candidates are conditional research signals with weaker evidence. Sizing Agent should independently check short permission, borrow/implementation constraints, portfolio risk, and risk budget; reject them if unsupported.
- Volatility and turnover are context for sizing and implementation, not instructions to derive a target weight from this packet.
- Empty side means no signal on that side. Do not fill the list by relaxing filters.

## Output files

- CSV: C:\Users\Danil\Desktop\pipeline\data\interim\aggressive_name_signals\name_level_signals.csv
- Report: C:\Users\Danil\Desktop\pipeline\docs\aggressive_name_signals_report.md
