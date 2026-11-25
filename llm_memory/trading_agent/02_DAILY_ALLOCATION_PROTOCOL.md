# Daily Protocol Pointer

Last updated: 2026-11-25

The canonical daily workflow is now [06_DAILY_TRADING_RESEARCH_LOOP.md](06_DAILY_TRADING_RESEARCH_LOOP.md).

This file is retained to avoid breaking older links. Earlier allocation-centric instructions, including any HOLD/no-change default, are superseded by the calibrated trading protocol dated 2026-11-25.

Daily trigger: user provides the final results for the actual portfolio, SBMX, and LQDT. Start with an audit of the previous decision and its counterfactual opportunity cost, then generate hypotheses and follow the canonical loop.

Hard constraints:
- Active trade actions: LONG or SHORT only; never HOLD.
- LONG LQDT is the neutral allocation when no equity trade has a sufficiently supported edge.
- Sizing must be derived and justified.
- One-use scripts: at most two passes before Qwen and at most two after Qwen.
- Commit every material decision-tree branch.
- Every script run must generate falsifiable hypotheses.
- Self-check and remove unsupported arguments.
- Reviews every 5 and 20 trading sessions use compressed context.
