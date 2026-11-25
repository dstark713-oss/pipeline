# Research Agent Memory

Last updated: 2026-11-25

This directory is the persistent working context for the Research Agent in `dstark713-oss/pipeline`. It is not user-facing product documentation. Keep it factual, compact enough to navigate, and explicit about uncertainty.

## Source of truth

- GitHub repository: [dstark713-oss/pipeline](https://github.com/dstark713-oss/pipeline)
- Current branch: `main`
- Project code and committed research artifacts are authoritative for what exists.
- This memory records role, decisions, rationale, status, observations, hypotheses, and next steps that are not obvious from code.
- Local `data/` is intentionally not committed. Its latest user-reported state is recorded here and must not be mistaken for a live inspection of local files.

## Read order

1. [Role and operating rules](01_ROLE_AND_RULES.md)
2. [Research workflow protocol](RESEARCH_WORKFLOW.md)
3. [Cumulative research knowledge](00_CUMULATIVE_KNOWLEDGE.md)
4. [Dataset pipeline state](02_DATASET_PIPELINE.md)
5. [Primitive research](03_PRIMITIVE_RESEARCH.md)
6. [Refresh mechanism](04_REFRESH_MECHANISM.md)
7. [Next steps and open risks](05_NEXT_STEPS.md)
8. [Research journal](RESEARCH_JOURNAL.md)
9. [Change log](CHANGELOG.md)

## Evidence labels

Use these distinctions in future updates:

- **Verified in GitHub**: inspected in the current repository branch.
- **User-run / user-reported**: the user executed it and supplied output.
- **Code-inspected, not run here**: implementation exists, but runtime success is not established.
- **Hypothesis / concern**: plausible interpretation or risk that still needs a test.
- **Decision**: explicitly agreed project rule.

Never promote a hypothesis into a fact. Never claim a script was executed merely because it is committed or its logic was inspected.

## Update protocol

- Update this directory whenever an important project decision, completed stage, result, blocker, or changed plan occurs.
- Prefer editing the smallest relevant memory file; update this index if files are added or reorganized.
- Keep chronological notes in `CHANGELOG.md` and `RESEARCH_JOURNAL.md`.
- Record exact paths, command lines, commit SHAs, data dates, and key output counts where available.
- Distinguish the current state from intended future architecture.
- Do not copy raw datasets, SQLite databases, Parquet files, logs, or bulky generated reports into GitHub memory.
- Use `docs/` for compact tool documentation and research-stage reports/results. Do not duplicate agent operating rules there; keep those in `llm_memory/research_agent/`.

## Project boundary

The Research Agent is an autonomous researcher and developer of validated analytical capabilities for financial-market analysis. Its outputs are reusable data, methods, models, analysis modules, tools, and documented knowledge. The separate Trading Agent consumes those capabilities; the Research Agent does not make trading or allocation decisions.

The first primitive research cycle and market-state screener hypothesis are closed. The screener is the first runtime tool, not the boundary of future research. The next cycle is now **ML direction prediction**, under the evaluation firewall documented in `01_ROLE_AND_RULES.md`: WF statistical/model metrics are allowed, a separate fixed IS/VAL split is not planned, and portfolio-level metrics are prohibited until final model approval. After approval, only one decisive portfolio-level run is permitted.

Important data constraint: the repository has an internal historical market-data pipeline, but **no internal fundamental-data dataset or pipeline**. News, market semantics, company context, and fundamental information are currently obtained from the internet/external sources. Such information must retain source and temporal provenance; present-day web information must not be treated as point-in-time historical data.


## Mandatory operating protocol

Every research stage follows the approval-gated sequence in [RESEARCH_WORKFLOW.md](RESEARCH_WORKFLOW.md): plan → user approval → implementation → compact docs outputs → analysis → agreed checks → code/results → next-stage proposal and approval. The cumulative knowledge file stores reusable cross-cycle findings; the journal stores chronology.
