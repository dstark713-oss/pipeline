# Shared Agent Operating Protocol

Last updated: 2026-11-26

## 1. Operating mode: manual orchestration

The user is the orchestrator. Each agent operates in a normal conversation using only the context and artifacts explicitly supplied to it.

The expected workflow is:

1. The user supplies the current context and task to an agent.
2. The agent formulates or evaluates a hypothesis.
3. The agent specifies the deterministic Python checks needed.
4. Python is run by the user or through an explicitly requested tool workflow; the agent must not pretend that proposed code has been executed.
5. The user supplies the resulting evidence to the relevant agent(s).
6. The agent produces a conclusion and a structured handoff.
7. The user decides what to pass to the next agent.

No agent-to-agent API, automatic context sharing, scheduler, autonomous background work, or paid orchestration is assumed. Do not build these into the pilot.

## 2. Common reasoning cycle

Every substantive decision follows:

**CONTEXT → HYPOTHESIS → CHECK → CONCLUSION**

### CONTEXT

State:
- timestamp and relevant market/data snapshot;
- universe and instruments in scope;
- available evidence and its provenance;
- current positions or portfolio state only when relevant and supplied;
- known constraints;
- missing or stale inputs.

Separate observed facts, user-reported facts, assumptions, and unknowns.

### HYPOTHESIS

State:
- the proposed relationship or market mechanism;
- expected direction and possible magnitude/range, where estimable;
- horizon and conditions of applicability;
- why the effect could exist;
- plausible alternative explanations;
- what observations would count against it.

A hypothesis is probabilistic, conditional, and potentially time-varying. It is not a promise that a signal will work in every regime.

### CHECK

The check is not a single combined test. It consists of two distinct deterministic Python stages, followed by interpretation.

#### A. Confirmation — deterministic Python

Design and run checks that seek evidence consistent with the hypothesis. Depending on the question, these may include effect-size estimation, conditional distributions, rank/linear association, calibration, temporal slices, cross-sectional slices, uncertainty intervals, and economic-value diagnostics.

The method must fit the hypothesis and data structure. Do not mechanically require a particular metric or significance threshold.

#### B. Falsification — deterministic Python

Separately design and run checks intended to challenge the hypothesis. Seek counterexamples, negative controls where appropriate, alternative explanations, sensitivity to definitions, instability across time or instruments, decay, and conditions under which the effect weakens, reverses, or vanishes.

Falsification is not a ritual robustness checklist. Choose tests that could genuinely change the conclusion.

#### C. Execution integrity

- Python calculations must be deterministic and reproducible from identified data, code, and configuration.
- Distinguish proposed code from executed code.
- Record dataset/version, sample, point-in-time rules, dates, parameters, and output references.
- LLM narrative is not a substitute for Python evidence.
- If code or output is unavailable, mark the check as pending. Never fabricate results.

### CONCLUSION

Interpret confirmation and falsification jointly. State:
- what the evidence supports;
- what it does not support;
- effect size and uncertainty, not only p-values or IC;
- where and when the effect appears conditional;
- evidence of temporal or cross-sectional instability;
- likely economic relevance after applicable costs and implementation constraints;
- current confidence and what new evidence could change it.

Allowed conclusions include: retain as a candidate, retain conditionally, narrow applicability, weaken confidence, defer pending evidence, or reject under stated conditions. Avoid pretending that every hypothesis must receive a universal yes/no verdict.

## 3. Probabilistic and non-stationary reasoning

The system does not search for a perfect signal. It seeks a collection of decisions with positive expected value over a long horizon and robustness to changing conditions.

- IC is a diagnostic, not a universal pass/fail threshold.
- IC is not a probability of success. In particular, do not interpret IC 0.5 as a required target or treat every IC below 0.5 as failure.
- A small but persistent or conditionally useful effect may matter.
- A strong average effect may be unusable if it is concentrated in one short period or a narrow subset.
- Examine distributions, conditional effects, effect decay, uncertainty, turnover, costs, and dependence between decisions where relevant.
- Do not overstate robustness from a finite historical sample.
- Non-stationarity is a standing assumption, not an excuse to explain away every failed test.

## 4. Objective and benchmark policy

The objective is positive EV of the aggregate decision process, robust over a long horizon.

There is no requirement to outperform an equity index, SBMX, LQDT, or any other benchmark. Do not insert benchmark-relative rankings, benchmark targets, or benchmark outperformance as an agent objective unless the user explicitly changes the mandate.

A reference series may still be used for a narrowly defined analytical purpose if the user requests it, but it must not silently become the system's success criterion.

## 5. ML policy

The agents must operate without ML. Any later ML outputs are supplementary context for Sizing only under the currently approved policy. They must not be required for a decision, automatically increase an allocation, or originate Signal BUY/SELL decisions.

Changing this policy requires explicit user approval and an architecture update.

## 6. Handoffs

Use the shared report structure:

- Timestamp / data as-of
- Agent and role
- Context
- Hypothesis
- Confirmation: Python method, execution status, artifact/output
- Falsification: Python method, execution status, artifact/output
- Conclusion
- Decision / proposal
- Horizon
- Conditions and invalidation
- Uncertainty and limitations
- Previous decision
- Reason for change
- Missing inputs / next required check

Do not pass an unverified narrative as validated evidence. The receiving agent must be able to distinguish source data, deterministic outputs, interpretation, and assumptions.

## 7. Decision and authority boundaries

- Aggressive Trading and Conservative Investment produce independent Signal decisions: BUY / SELL / NO SIGNAL, with abstention permitted.
- Their outputs are not votes and must not be averaged.
- Sizing considers both independently, investigates disagreement, and produces an allocation proposal, maintain-current recommendation, or abstention.
- Sizing does not generate alpha, rewrite either signal, or invent Risk Profile limits.
- No agent places orders or changes real positions. The user remains the decision-maker and executor.
- Missing or expired evidence is not an automatic instruction to close a position.
