# Trading Agent Memory Changelog

## 2026-11-25: calibrated trading loop
- Replaced portfolio-maintenance / HOLD-oriented framing with short-horizon trading research: what to LONG or SHORT today, on which horizon, and at what justified size.
- Set daily input contract: final actual-portfolio, SBMX, and LQDT results; audit the previous decision and its counterfactual opportunity cost before new analysis.
- Added immutable decision journal and outcome attribution; mandatory 5- and 20-trading-session reviews with compressed context.
- Set strict script budget: two passes before Qwen (first run, result analysis) and two after Qwen; scripts simple, read-only by default, reproducible, compact, and hypothesis-generating.
- Required a fresh decision tree with self-check; unsupported arguments are excluded, not retained as caveats.
- Required committing every material decision-tree branch/leaf to GitHub.
- Defined LONG/SHORT action vocabulary; LONG LQDT is the neutral opportunity-cost allocation when no equity direction has a sufficiently supported edge. No forced risky trade.
- Made sizing mandatory and evidence-derived; prior ownership and small position size are not justifications.
- Clarified that Qwen is an adversarial reviewer, not a vote; user operates Qwen and supplies the review.
- Deleted all nine files previously present in scripts/one_use. The directory is now empty/absent on GitHub because Git does not retain empty directories.
- Marked previous HOLD recommendation and 2026-11-23 portfolio allocation as historical only, not current verified state.

## 2026-11-24
- Archived earlier allocation-centric work and decision tree. Its conclusions remain historical evidence, not current instructions.
