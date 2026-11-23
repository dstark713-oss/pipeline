# Trading Agent Research Journal

Chronological log of role setup, daily allocation investigations, decisions, tool audits, and lessons. This journal belongs to the Trading Agent and is separate from the user's daily report and the Research Agent's journal.

## 2026-11-23 | Agent initialization and repository reconnaissance

### Initial setup

The user defined a daily workflow triggered by "Аллокация на сегодня". The initial setup documented portfolio review, local market tools, news, fundamentals, semantic analysis, Qwen-only review, allocation synthesis, and a future API direction.

### Repository reconnaissance

Inspected the repository root, `llm_memory/`, existing specialist-agent memories, the deterministic screener specification, the dataset refresh implementation, and relevant script inventories.

Existing deterministic stack:
- `scripts/dataset/fresh/refresh_pipeline.py`
- `scripts/experiments/primitives/05_build_primitive_features.py`
- `scripts/tools/01_primitive_screener.py`
- `docs/tools/01_primitive_screener.md`

The screener exposes instrument state (`drawdown_60`, `zscore_sma20_20`, `realized_vol_60`) and separate market context (`breadth_change_5`, `breadth_sma20`). It is descriptive/read-only and does not generate buy/sell signals or portfolio weights. Local runtime status is not established by repository inspection.

## 2026-11-23 | Role correction: learn allocation through real-market cycles

### User correction

The user clarified that the Trading Agent's immediate and only responsibility is supervised allocation reasoning on the real market. The user also clarified the practical research handoff: when information is missing from existing tools, the agent should create a focused one-use script, the user runs it locally, and returns the result. The script may be provided in chat or committed to GitHub for the user to pull. Future Codex/Python access should enable direct analysis of accessible project data.

### Current allocation baseline

User-reported:
- T: 10%
- GCHE: 2%

The remaining 88% is not classified. Do not call it cash or assume it is deployable.

### Agreed operating split

- Portfolio Reader: maintain a simple allocation ledger from the user's updates; no complex reader.
- Daily Market Snapshot: request local market/screener outputs from the user.
- News & Fundamentals: agent gathers current public information from the internet.
- Semantic Engine: agent performs direct LLM reasoning over sourced facts and events.
- Qwen Reviewer: user runs Qwen and supplies its response; Qwen is the only second-opinion LLM.
- Allocation Engine: agent's own reasoning and recommendation; maintain this journal.
- Research gaps: agent specifies the missing information and creates a complete, read-only one-use script where practical; user executes and returns outputs.
- API orchestration: deferred until the agent has been trained through repeated real-market cycles.

### One-use script policy

Planned path: `scripts/one_use/`. Create the directory with the first actual script rather than adding empty scaffolding. Scripts must have a narrow research question, explain decision relevance, use read-only access by default, avoid production data mutation, define outputs and run instructions, and remain marked unexecuted until the user returns results.

### Learning protocol

The agent should form an independent thesis before reading Qwen's response where practical, request adversarial review from Qwen, compare both views against primary evidence, propose an allocation with counterarguments and invalidation conditions, then preserve the decision and later evaluate the outcome. Do not confuse a profitable outcome with a sound process or a loss with a bad decision.

### Evidence status

- Current allocation T 10%, GCHE 2%: user-reported.
- Local market snapshot for this decision: not yet supplied.
- Full composition of remaining 88%: unknown.
- No Qwen review result yet supplied for this cycle.
- No allocation change has been recommended or executed.
- No one-use script has been required or created yet.