# Trading Agent Memory Changelog

## 2026-11-24
- Added the allocation decision tree and recorded the 2026-11-24 HOLD / NO CHANGE recommendation using the latest supplied local snapshot dated 2026-11-23.
- Corrected the known portfolio baseline to T 10%, GCHE 2%, LQDT 88%; LQDT is a money-market fund, not idle cash.
- Recorded user constraints: maximum 10 simultaneous equity names and aggregate signed portfolio loading from -0.5 to +1.5.
- Explicitly recorded that no per-security weight cap or separate gross-exposure cap was supplied.
- Documented the origin of 3%/6%/9%/12% equity scenarios as 12% baseline multiplied by breadth rule factors 25%/50%/75%/100%.
- Recorded the fixed historical cash proxy of 8% annual effective (user-provided RGBITR minus RGBI derivation), distinct from the current estimated LQDT yield of approximately 12%.
- Recorded the T and GCHE 9M 2026 fundamental evidence, counterarguments, invalidation conditions, and confidence.
- Excluded sensitivity checks from the current breadth experiment.
- Marked the corrected breadth backtest and 2026-11-24 local snapshot as pending; no local execution or order execution claimed.

## 2026-11-23
- Created the Trading Agent's dedicated memory directory.
- Defined the initial human-orchestrated daily allocation protocol and Qwen-only second-opinion policy.
- Recorded existing deterministic market-state tools and their limitations.
- Corrected the operating priority: the agent's sole current job is supervised real-market allocation reasoning and learning.
- Replaced complex portfolio-reader assumptions with a simple user-updated allocation ledger.
- Established user-supplied Daily Market Snapshot, agent-led internet research for news/fundamentals, direct LLM semantic reasoning, and user-operated Qwen review.
- Deferred API orchestration and tool-building until repeated manual allocation cycles reveal a concrete need.
- Added the one-use research-script handoff: agent identifies the gap and writes a complete script under `scripts/one_use/`; user runs it and returns outputs.
- Recorded future Codex/Python access as a later capability, not a current assumption.
