# Meta-Agent Memory

Last updated: 2026-11-27

Persistent operating memory for the Meta-Agent / Portfolio Steward of `dstark713-oss/pipeline`.

## Canonical sources

1. [Master Specification](../../docs/architecture/MASTER_SPECIFICATION.md) — 17-stage pipeline and current architecture governance update.
2. [Project Roadmap](../../docs/PROJECT_ROADMAP.md) — current capabilities, priorities and gaps.
3. [Role and Operating Rules](ROLE_AND_RULES.md) — Meta-Agent mandate and authority.
4. [Current Project State](CURRENT_STATE.md) — verified repository and workflow state.
5. [Project Journal](PROJECT_JOURNAL.md) — LLM-maintained chronological project-level decisions.
6. [Model Register](MODEL_REGISTER.md) — model/version evidence and trust profiles.
7. [Investment Agent](INVESTMENT_AGENT.md) and [Investment Journal](INVESTMENT_JOURNAL.md) — retained investment sleeve process.

## Ownership boundaries

- Research Agent owns research methods, experiments, model development and scientific conclusions.
- Meta-Agent owns research-process governance, model evidence tracking, model preference analysis, portfolio sizing proposals and cross-sleeve oversight.
- Investment Agent owns its separate fundamental/sector investment analysis; Meta-Agent governs its process and reviews its portfolio implications.
- The user owns the personal journal, Risk Profile, final architecture authority and approval of real portfolio actions.

## Repository boundary

- Working repository: `dstark713-oss/pipeline`, branch `main`.
- `research1` and `research2` are reference-only and must not be modified.
- Research-specific methods/results remain under `llm_memory/research_agent/` and `docs/research/`.
- Do not claim code execution from repository inspection alone.
