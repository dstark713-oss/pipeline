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


## 2026-11-23 | Research Agent role and scope correction

- Rewrote `01_ROLE_AND_RULES.md` to define the Research Agent as an autonomous researcher/developer of validated analytical capabilities, with the Trading Agent as a separate downstream consumer.
- Updated the directory index and project boundary in `README.md`.
- Recorded closure of the first primitive research and market-state screener hypothesis.
- Replaced the premature breadth-downside follow-up with a capability/gap assessment as the next research cycle.
- Explicitly recorded that no internal fundamental-data dataset or pipeline exists; semantic, news, company, and fundamental context is retrieved from external internet sources and must retain temporal/source provenance.
- No Python/project code, Trading Agent files, or user diary artifacts were changed.
