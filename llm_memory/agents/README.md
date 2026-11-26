# Conversational Agent Pilot

Status: user-approved manual pilot, 2026-11-26.

## Purpose

This directory defines three role-specific agents for a practical, manually orchestrated pilot:

1. **Aggressive Trading** — Qwen.
2. **Conservative Investment** — ChatGPT.
3. **Sizing** — ChatGPT.

The user is the orchestrator. The agents are currently used through ordinary conversations and manually supplied context, hypotheses, Python outputs, and handoffs. There is no agent API, autonomous runtime, background execution, or paid orchestration layer in this pilot.

The purpose is to establish usefulness before automation. Do not design or imply infrastructure that does not exist.

## Canonical documents

- [Shared operating protocol](shared/OPERATING_PROTOCOL.md)
- [Aggressive Trading role](aggressive_trading/ROLE.md)
- [Conservative Investment role](conservative_investment/ROLE.md)
- [Sizing role](sizing/ROLE.md)
- [Master Specification](../../docs/architecture/MASTER_SPECIFICATION.md)

## Common reasoning cycle

**CONTEXT → HYPOTHESIS → CHECK → CONCLUSION**

The CHECK stage is mandatory and has three ordered parts:

1. **Confirmation** — deterministic Python analysis designed to find evidence consistent with the hypothesis.
2. **Falsification** — a separate deterministic Python analysis designed to challenge the hypothesis, identify counterexamples, and test where the effect weakens or disappears.
3. **Conclusion** — interpret both outputs together, including uncertainty, conditionality, and non-stationarity.

Do not collapse confirmation and falsification into one test or a binary verdict.

## Operating principles

- No ML dependency. The agents must be useful with currently available data, deterministic tools, and explicit reasoning.
- Future ML outputs, if introduced, are supplementary information for Sizing only under the current policy. They are not required inputs and do not independently create BUY/SELL decisions.
- No benchmark mandate. The objective is positive expected value (EV) across the aggregate of decisions, robust over a long horizon. Beating an index or LQDT is not the task.
- No perfect-signal requirement. Signals are probabilistic and non-stationary. A low IC, or an IC below 0.5, is not by itself grounds to kill a hypothesis.
- Do not confuse a weak effect with no effect, statistical significance with economic value, or historical association with a stable future relationship.
- No fabricated certainty, data, constraints, or numerical Risk Profile limits.
- Agents provide analysis and proposals; the user retains orchestration and all authority over real actions.

This is a conversational pilot, not a declaration that the target production architecture is implemented.
