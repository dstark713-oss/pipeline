# Research Agent Memory Changelog

## 2026-11-23

- Created the Research Agent memory directory as the persistent context for the MOEX dataset/primitive-research workflow.
- Recorded the user's role boundaries, repository hygiene, approval process, and prohibition on premature production screener work.
- Consolidated the historical universe, raw daily history, audit, corporate-action adjustment, and PIT TOP50 panel state.
- Recorded exact primitive formulas, first-pass IC/Rank IC observations, breadth results, and diagnostics required before feature selection.
- Documented the current refresh script as code-inspected but not runtime-validated; highlighted its no-backfill behavior and checkpoint/cutoff risks.
- Moved project context out of `docs/` conceptually; `docs/` is reserved for tool instructions, with only `docs/tools/00_refresh_ds.md` retained as the planned exception.

- Reviewed research documentation, committed experiment implementations, and the user's daily_report.txt entries for 2026-11-22 and 2026-11-23. Added a separate Research Agent journal; left the user's journal untouched.
- Updated screener documentation: realized_vol_60 TOP 15 is ascending (quietest to more volatile), matching the implementation.
- Recorded the user-proposed breadth allocation heuristic and the exact-50% boundary mismatch between the agreed >= 50% rule and portfolio code's > 50% classification.
- Replaced stale deferred-screener next steps with a proposed conditional downside-risk study of the four breadth regimes. This is a proposal, not an approved implementation.
