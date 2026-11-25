# Research focus update — 2026-11-26

## Strategic decision
The primitive research and ML_1 model experiments have produced no demonstrated edge. No signal means no trading: suspend active trading workflow and focus fully on substantive research. Do not infer or fabricate an edge from weak or inconclusive results.

## Repository cleanup / suspension
Primitive screener and Model 1/ML_1 code, docs, experimental scripts and agent contexts were removed from main to reduce clutter and context/usage overhead. These experiments may be revisited later, but are not active. Agent contexts for Qwen and Trading ChatGPT were deleted. Trading agents may return in the future, but their downstream task will be driven by validated model signals, not primitives or discretionary heuristics.

## What remains active
- Primary focus: EDA2 research in the existing pipeline, with blocks 1-4 completed or analyzed (block 2 interpretation has been completed in conversation; block 4 analyzed).
- Next EDA2 order remains 5 -> 6 -> 7, following the approved sequence (prior order was 1 -> 2 -> 4 -> 5 -> 6 -> 7; block 3 completed earlier and is not revisited).
- Block 5 plan has not yet been approved/implemented in this current decision. Resume research, not infrastructure audits.
- Dataset-quality work is maintenance only. Do not expand each research task into audits, repeated checks, or dataset rebuilding. Fix only concrete issues blocking the current research result.
- Continue following the research workflow: agree on scope/plan before code; user runs code locally; analyze actual outputs; propose checks only when needed; no claims of local execution without evidence.
- Keep DS-first methodology, with no trader indicators, technical signals, trading rules, BUY/SELL or target weights during EDA.

## Reason for pause
Primitive analyses and the first predictive model (ML_1) did not establish an edge. Treat that as a research finding and a reason to redirect effort, not a reason to keep trading based on unsupported signals.

## Future agents
If/when agent workflows are restored, the agent decision layer must consume validated model signals. Agents are not to independently generate trading logic in the absence of validated signals.
