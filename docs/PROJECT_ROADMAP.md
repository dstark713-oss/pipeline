# Project Roadmap

**Status:** strategic transition map, not an authorization to implement every item.  
**North star:** `docs/architecture/MASTER_SPECIFICATION.md`.

## Guiding rule

Develop the system in dependency order. Research and data infrastructure continue to evolve on their own approved track; architecture work must not interrupt active research or take over the Research Agent's domain.

The roadmap distinguishes existing capability, missing capability, and a possible implementation sequence. It does not invent the names or reorder the user's 17 research-pipeline stages.

## 1. Current foundation

The `pipeline` repository currently provides:
- MOEX ISS market-data collection and incremental refresh;
- raw and adjusted dataset construction;
- historical point-in-time universe/panel infrastructure;
- isolated statistical and ML research experiments;
- research documentation and a Research Agent context area.

The root README and project documentation define the current repository scope. Local databases and generated datasets are not committed.

## 2. Target capabilities and gaps

| Capability | Target state | Current status |
|---|---|---|
| Data and research foundation | Reproducible, point-in-time datasets and validated analytical capabilities | Partially implemented; MOEX research foundation exists |
| Quant Research workflow | Qwen-led exploration plus independent GPT critique and evidence-backed handoff | Research workflow/context exists; multi-model operating protocol not yet implemented as a system |
| Signal LLM | BUY / SELL / NO SIGNAL from approved evidence | Not implemented as a formal component |
| Aggressive Trading profile | Higher-opportunity application of approved evidence | Role defined; runtime not implemented |
| Conservative Investment profile | Strict evidence/stability selection profile | Role defined; runtime not implemented |
| Sizing LLM | Allocation proposal under approved Risk Profile | Not implemented as a formal component |
| Python Risk Engine | Deterministic calculation and hard-constraint validation | Not implemented as a formal component |
| Meta-Agent | Repository, agent, configuration, research-request and lifecycle governance | Role defined; dedicated memory is being established; runtime not implemented |
| Agent interfaces and audit trail | Typed inputs/outputs, provenance, logs and versioned contracts | Not implemented as a complete system |
| Promotion lifecycle | Tests, shadow evaluation, explicit promotion and rollback | Not implemented as a complete system |
| Multi-asset support | Generalized data/research contracts beyond current MOEX scope | Future capability; current repository is MOEX-focused |

## 3. Dependency-ordered transition

### Phase A — Establish governance and canonical context
- Keep the Master Specification as the architecture source of truth.
- Maintain separate persistent memory for Meta-Agent and Research Agent.
- Define ownership, permissions, handoff contracts, and evidence labels.
- Keep current implementation separate from target-state descriptions.

**Exit criteria:** one canonical architecture; no ambiguity about who owns research, signal selection, sizing, controls, or governance; agent memories point to canonical sources.

### Phase B — Stabilize research-to-capability handoff
- Research Agent produces reproducible, versioned analytical capabilities.
- Qwen proposes and explores; GPT independently critiques using the underlying evidence.
- The Meta-Agent verifies provenance, status, tests, and handoff completeness without rewriting scientific conclusions.
- Promotion of a research output for downstream use requires an explicit decision.

**Exit criteria:** a consumer can identify exactly which validated capability/version it is using and what evidence supports it.

### Phase C — Specify deterministic control foundation
- Define the Risk Profile as a user-owned configuration.
- Specify portfolio state, exposure calculations, instrument constraints, and validation interfaces.
- Implement numerical logic in Python with independent tests.
- Keep all numerical limits explicit and versioned; do not infer them from model outputs.

**Exit criteria:** deterministic tests cover the agreed calculations and hard constraints; invalid proposals are rejected.

### Phase D — Build directional Signal layer
- Define typed signal inputs/outputs, timestamps, validity, evidence provenance, and no-signal behavior.
- Implement Aggressive and Conservative profiles as separate configurations/decision policies.
- Restrict both profiles to approved research capabilities.
- Test against historical and shadow inputs before any operational use.

**Exit criteria:** reproducible signal decisions with model/configuration versions, traceable evidence, and explicit abstention behavior.

### Phase E — Build Sizing layer
- Define the interface from approved signals and portfolio state to proposed weights.
- Implement sizing proposals with ChatGPT as the reasoning layer.
- Validate every numerical output through the Python Risk Engine.
- Ensure sizing cannot alter signals or Risk Profile constraints.

**Exit criteria:** proposals are reproducible, independently validated, and rejected when constraints fail.

### Phase F — Integrate Meta-Agent lifecycle governance
- Register agents, versions, permissions, configurations, and dependencies.
- Add change proposals, diffs, test records, shadow evaluation, promotion, and rollback.
- Preserve user approval for material changes and all live actions.

**Exit criteria:** changes are auditable and reversible; no agent can silently promote itself or alter live positions.

### Phase G — Expand scope deliberately
- Generalize data contracts and asset-specific adapters beyond MOEX only when there is a concrete requirement.
- Preserve point-in-time and provenance standards across markets.
- Do not expand asset coverage at the expense of correctness in the existing pipeline.

**Exit criteria:** each added market has documented source semantics, coverage, temporal rules, validation, and reproducible data construction.

## 4. Cross-cutting acceptance criteria

Every phase must satisfy:
- clear owner and permission boundary;
- explicit input/output contract;
- versioned code and configuration;
- reproducible tests and provenance;
- separation of LLM reasoning from deterministic calculations;
- failure and abstention behavior;
- documented limitations;
- human approval at the required governance gates.

## 5. Non-goals and prohibitions

- No automatic broker execution or order submission.
- No autonomous modification of real positions.
- No LLM-owned numerical hard limits.
- No sizing model that generates alpha.
- No Signal model that silently changes portfolio weights.
- No promotion based solely on a backtest or a statistically significant result.
- No Meta-Agent takeover of Research Agent methodology or conclusions.
- No reconstruction or renaming of the 17 research stages in this roadmap.

## 6. Roadmap maintenance

The Meta-Agent owns this roadmap. Update it when a capability is implemented, validated, promoted, blocked, or explicitly descoped. Every status change must link to repository evidence or a user decision. Do not mark a component complete merely because its role has been described.
