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
- Replaced stale deferred-screener next steps with a proposed conditional downside-risk study of the four breadth regimes. This was a proposal and is now superseded.

## 2026-11-23 | Research Agent role and scope correction

- Rewrote `01_ROLE_AND_RULES.md` to define the Research Agent as an autonomous researcher/developer of validated analytical capabilities, with the Trading Agent as a separate downstream consumer.
- Updated the directory index and project boundary in `README.md`.
- Recorded closure of the first primitive research and market-state screener hypothesis.
- Replaced the premature breadth-downside follow-up with a capability/gap assessment as the next research cycle.
- Explicitly recorded that no internal fundamental-data dataset or pipeline exists; semantic, news, company, and fundamental context is retrieved from external internet sources and must retain temporal/source provenance.
- No Python/project code, Trading Agent files, or user diary artifacts were changed.

## 2026-11-23 | Direction-prediction project and evaluation firewall

- Approved the next Research Agent project: ML prediction of price-movement direction.
- Recorded the initial range-position hypothesis as a research starting point, not a proven effect.
- Added the binding prohibition on inspecting, calculating, reporting, comparing, or using portfolio-level metrics before final model approval.
- Explicitly allowed statistical/predictive metrics on WF and recorded that the user will not create a separate fixed IS/VAL split.
- Limited portfolio evaluation to one decisive run after final model approval; portfolio results must not feed back into tuning or model selection.
- Updated the Research Agent's active project, next steps, and operating rules. No model code or portfolio evaluation was run.
