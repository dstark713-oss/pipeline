# Trading Agent Memory Changelog

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
- Recorded current user-reported baseline: T 10%, GCHE 2%; remaining 88% unclassified.
- No project code, research methodology, or order-execution capability was added.