# Project Roadmap

**Last updated:** 2026-11-27  
**Architecture source:** [Master Specification](architecture/MASTER_SPECIFICATION.md)  
**Governance memory:** [Meta-Agent](../llm_memory/meta_agent/README.md)

## North star

Build a reproducible research pipeline that produces validated analytical models. Use model outputs as the source of trading signals. The Meta-Agent governs research quality, model trust and portfolio sizing. A separate Investment Agent manages the fundamental investment sleeve.

The original 17 pipeline stages remain unchanged.

## Current foundation

- MOEX ISS data acquisition and refresh.
- Historical universe, adjusted datasets and PIT TOP50 panel.
- Reproducible research experiments and EDA2 results through block 5.
- Research Agent workflow and persistent memory.
- Meta-Agent project governance and Investment Agent memory.

The repository is a research/data foundation, not a completed production trading platform.

## Active operating model

| Responsibility | Owner | Current status |
|---|---|---|
| Research and model development | Research Agent; underlying LLM may vary | Active |
| Model validation and scientific conclusions | Research Agent | Active |
| Model/version evidence and trust tracking | Meta-Agent (ChatGPT) | Policy defined; evidence accumulation pending |
| Conditional model preference | Meta-Agent (ChatGPT) | Pending comparable model evidence |
| Trading signal source | Validated research model | No production-eligible model registered yet |
| Model-sleeve sizing and portfolio oversight | Meta-Agent (ChatGPT) | Conversational/manual |
| Fundamental investment analysis | Investment Agent (ChatGPT) | Active; sector-first |
| Investment-sleeve sizing and cross-sleeve oversight | Meta-Agent (ChatGPT) | Conversational/manual |
| Real trade execution | User | Manual approval required |

## Capital architecture

- 50% strategic allocation to model-driven trading.
- 50% strategic allocation to the separate investment sleeve.
- The 50/50 split does not require full deployment. Cash is valid within either sleeve.
- Do not reallocate the strategic split without explicit user approval.

## Priority sequence

### 1. Continue the research program
- Preserve the Research Agent's approved scope and workflow.
- Prioritize substantive statistical research and model development over conversational agent orchestration.
- Every model output must be traceable to a version, data snapshot, target/horizon and validation artifact.
- Keep scientific conclusions and experiment ownership with the Research Agent.

### 2. Build an evidence-based model record
- Record model identity/version, target, horizon, universe, dataset, WF protocol, coverage, predictive metrics, calibration, uncertainty, stability and failure modes.
- Separate research, validation, shadow/paper and live evidence.
- Compare models on common protocols where possible.
- Do not create a scalar trust score or leaderboard without a user-approved methodology and sufficient evidence.

### 3. Operate the model-driven sleeve
- Meta-Agent receives eligible model outputs and assesses validity, uncertainty and portfolio context.
- Meta-Agent proposes sizing under the user's Risk Profile and actual portfolio state.
- A model under research or validation is not a live signal source.
- Unused capital remains in cash rather than being forced into trades.

### 4. Maintain the Investment Agent
- Keep sector-first analysis before company selection.
- Require business economics, fundamental source provenance, valuation context and falsification.
- Keep the investment thesis independent of model trading signals.
- Meta-Agent reviews process quality and sizing implications.

### 5. Establish later automation only if justified
- Do not build an expensive multi-agent API orchestration layer now.
- Automate only workflows whose repeated manual value has been demonstrated.
- Any future execution automation requires separate explicit authorization and deterministic risk controls.

## Hard constraints

- No automatic broker execution or order submission.
- No autonomous real-position changes.
- No invented Risk Profile limits.
- No promotion based solely on in-sample performance or one backtest.
- No conflation of research, shadow/paper and live evidence.
- No benchmark-outperformance mandate.
- No Meta-Agent takeover of research methodology or scientific conclusions.
- The user's personal journal remains user-owned and unmodified.

## Roadmap maintenance

Meta-Agent updates this file when the user changes architecture or when a capability is implemented, validated, promoted, blocked or retired. Status claims must link to repository evidence or a user decision.
