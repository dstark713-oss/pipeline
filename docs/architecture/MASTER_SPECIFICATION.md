# Master Specification: System Architecture

**Status:** canonical target architecture  
**Repository:** `dstark713-oss/pipeline`  
**Scope:** target system and operating boundaries. This document does not claim that every target component is implemented.

## 1. Purpose

Build a systematic, multi-asset quantitative research and position-trading platform. The system develops evidence-backed analytical capabilities, converts approved evidence into instrument-level directional decisions, allocates capital under explicit constraints, and maintains a controlled lifecycle for models, agents, and configuration.

The platform is not a monolithic autonomous trading bot. Research, signal generation, sizing, deterministic controls, and orchestration are separate responsibilities with explicit interfaces.

The research program is organized around the user's 17-stage Quant Research Pipeline. This specification preserves that pipeline as a governing research framework; it does not recreate or rename its stage catalog. The exact stage definitions remain owned by the canonical research plan.

## 2. System architecture

The target architecture has three top-level system components:

1. **Signal LLM** — evaluates approved analytical evidence and produces a directional instrument-level decision: BUY, SELL, or NO SIGNAL. It does not determine position size or override portfolio constraints.
2. **Sizing LLM** — translates approved signals and portfolio context into proposed capital allocations within the active Risk Profile and deterministic constraints. It does not generate alpha.
3. **Meta-Agent** — governs the lifecycle of the system: repository state, agent instructions, research requests, evidence review, configuration changes, versioning, testing, shadow evaluation, promotion, and rollback.

A deterministic Python Risk Engine independently calculates and validates numerical constraints. It is a hard-control layer, not an LLM persona and not a substitute for human authorization.

## 3. Functional roles and model assignment

Five functional roles operate within the architecture. A role is a responsibility boundary, not necessarily a separate executable process.

| Functional role | Primary responsibility | Model assignment |
|---|---|---|
| Meta-Agent | System architecture, repository and agent lifecycle, governance | ChatGPT |
| Quant Research | Discover and test analytical capabilities; formulate hypotheses and experiments | Qwen primary researcher; GPT independent methodological critic |
| Sizing | Portfolio allocation proposals under approved constraints | ChatGPT, with deterministic Python Risk Engine validation |
| Aggressive Trading | Apply approved evidence with a higher-opportunity, shorter-horizon selection profile | Qwen |
| Conservative Investment | Apply stricter evidence quality, stability, and lower-turnover selection criteria | ChatGPT |

### 3.1 Role boundaries

**Quant Research**
- Owns research questions, hypotheses, data analysis, experiment design, statistical interpretation, and research conclusions.
- Qwen may lead exploration and propose analytical candidates.
- GPT independently challenges methodology, leakage, overfitting, statistical inference, robustness, and economic interpretation.
- The critic must have access to the underlying data, methodology, code, settings, and results, not only a summary.
- Research outputs are candidates until explicitly validated and approved for downstream use.

**Aggressive Trading**
- Searches for opportunities using approved models, signals, and evidence.
- May apply momentum, breakout, trend-following, or other explicitly approved strategy logic.
- Aggressiveness describes opportunity selection and review cadence. It never grants permission to exceed risk constraints or bypass validation.

**Conservative Investment**
- Applies stricter standards for evidence quality, persistence, robustness, and uncertainty.
- Favors lower turnover and longer evaluation horizons where appropriate.
- Evaluates candidate attractiveness; it does not allocate capital.

**Sizing**
- Consumes approved signals, portfolio state, and the active Risk Profile.
- Produces proposed weights/exposures and reasons for constraints, reductions, or rejection.
- Does not invent directional alpha or modify the signal's meaning.
- All numerical constraints are independently checked by deterministic code.

**Meta-Agent**
- Owns the system-level view and coordinates boundaries between roles.
- Does not perform Quant Research's analysis or decide its scientific conclusions.
- Does not choose the user's risk appetite or invent risk limits.
- Does not become an unapproved trading decision-maker.

## 4. Signal and sizing contracts

### Signal contract

The Signal layer produces an instrument-level directional state:
- `BUY`
- `SELL`
- `NO SIGNAL`

Each decision must be traceable to approved model versions, evidence, timestamps, instrument identity, and applicable validity conditions. The signal layer does not output portfolio weights.

Aggressive Trading and Conservative Investment are distinct selection profiles within this directional decision layer. They may differ in horizon, evidence thresholds, turnover tolerance, and opportunity selection, but both consume only approved analytical capabilities.

### Sizing contract

Sizing consumes:
- approved directional signals and their provenance;
- current portfolio positions and available capital;
- the active, user-approved Risk Profile;
- deterministic portfolio and instrument constraints.

Sizing returns a proposed allocation, explanation, and constraint/rejection reasons. It cannot change the Risk Profile or weaken hard controls.

### Deterministic Risk Engine

Python is authoritative for numerical calculations and hard constraints, including exposure aggregation, concentration, and other explicitly configured limits. LLM-generated arithmetic is never the enforcement mechanism. A failed validation blocks promotion of the proposed allocation.

This specification does not define numerical risk limits. Those belong to a separately approved Risk Profile.

## 5. Meta-Agent governance

The Meta-Agent maintains a controlled lifecycle:

1. Discover and classify repository state and evidence.
2. Maintain canonical architecture and agent-specific memory.
3. Route work to the correct functional owner.
4. Review outputs against the owner's contract and required evidence.
5. Propose configuration or code changes with a clear diff and rationale.
6. Obtain user approval where required.
7. Version changes and run deterministic tests.
8. Evaluate changes in shadow mode before promotion where the change affects system behavior.
9. Preserve rollback paths and record the promotion decision.

The Meta-Agent may coordinate and audit the research process, but must not silently take over research ownership. It checks whether research artifacts exist, whether statuses are synchronized, and whether handoffs are complete. Scientific methods, calculations, interpretation, and conclusions belong to Quant Research.

## 6. Human authority and execution boundary

- Trade execution is manual.
- No broker API or automatic order submission is in scope.
- No agent may automatically modify real portfolio positions.
- Any action affecting a real position requires explicit human confirmation.
- The absence or expiry of a signal is not, by itself, an instruction to close a position.
- LLMs do not replace deterministic calculations or hard controls.
- The user retains authority over strategic decisions, Risk Profile, live actions, and promotion to production.

## 7. Evidence, versioning, and promotion

Every material output must identify its provenance: data snapshot, code revision, model/configuration version, parameters, execution status, and limitations.

A backtest is not live performance. Statistical significance is not equivalent to economic value. A model or agent configuration is not production-ready merely because it produces plausible output.

Production-affecting changes require:
- explicit diff and rationale;
- reproducible tests;
- independent deterministic checks where applicable;
- shadow evaluation against the current version;
- an explicit promotion decision;
- a documented rollback path.

The Meta-Agent coordinates this process. It must not claim a test or local run succeeded without execution evidence.

## 8. Current implementation versus target architecture

The current `pipeline` repository is research and data infrastructure for systematic analysis of the Russian equity market using MOEX ISS data. It contains market-data collection/refresh, dataset construction, point-in-time panel work, and isolated research experiments.

The following target components are architectural goals, not claims about existing implementation:
- Meta-Agent runtime and governance automation;
- Signal LLM and its Aggressive/Conservative profiles;
- Sizing LLM;
- deterministic Python Risk Engine;
- formal agent-to-agent interfaces and audit logs;
- configuration registry, shadow evaluation, promotion, and rollback workflows;
- multi-asset expansion beyond the current MOEX research scope.

Never describe a target component as implemented until code, tests, and operational evidence support that status.

## 9. Ownership map

| Domain | Owner |
|---|---|
| System architecture, repository governance, agent memory and lifecycle | Meta-Agent |
| Research methodology, datasets for experiments, statistical analysis, conclusions | Quant Research |
| Directional opportunity selection using approved evidence | Signal roles |
| Capital allocation proposal | Sizing |
| Numerical hard limits and calculations | Python Risk Engine |
| Risk appetite, strategic approvals, live actions, production promotion | User |

This ownership map is binding unless the user explicitly changes it.
