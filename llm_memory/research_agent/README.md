# Research Agent Memory

Last updated: 2026-11-27

Persistent working context for the Research Agent in `dstark713-oss/pipeline`. This is operational context, not a transcript. Validated analytical capabilities are delivered downstream; trading decisions, portfolio sizing, and real execution remain outside the Research Agent's authority.

## Source of truth

- Repository: [dstark713-oss/pipeline](https://github.com/dstark713-oss/pipeline), branch `main`.
- Committed code and research artifacts define what exists.
- Local `data/` is not committed. User-run results committed under `docs/` are evidence of the recorded local run, not an independent rerun by the Research Agent.
- Evidence must be labeled as GitHub-verified, user-run/user-reported, code-inspected-not-run, independently runtime-verified, or hypothesis.

## Read order

1. [Role and operating rules](01_ROLE_AND_RULES.md)
2. [Research workflow protocol](RESEARCH_WORKFLOW.md)
3. [Cumulative research knowledge](00_CUMULATIVE_KNOWLEDGE.md)
4. [Dataset pipeline state](02_DATASET_PIPELINE.md)
5. [Primitive research](03_PRIMITIVE_RESEARCH.md)
6. [Refresh mechanism](04_REFRESH_MECHANISM.md)
7. [Current stage and next steps](05_NEXT_STEPS.md)
8. [ML research context](06_ML_DIRECTION_FEATURE_RESEARCH.md)
9. [Research journal](RESEARCH_JOURNAL.md)
10. [Change log](CHANGELOG.md)

## Current project

**Current stage:** STAGE 05 — Hypothesis Research. The architecture, two economic categories, seven-hypothesis initial pool, research plan, registry and priority order are documented and approved. No hypothesis experiment has been run.

- Hypothesis passports: `docs/research/research_hypothesis/`
- Plan and results: `docs/research/hypothesis_research/`
- Stage specification: `docs/architecture/MASTER_SPECIFICATION.md`
- EDA2 synthesis: `docs/research/eda2/results/compilation/EDA2_RESULTS_COMPILATION.md`

The two categories are Risk Control and Direct Monetization. Hypothesis approval means approval to investigate, not empirical support. The next step is a formal research design for the selected hypothesis, approved before implementation.

## Mandatory operating protocol

Every stage follows `RESEARCH_WORKFLOW.md`: plan → user approval → implementation → compact docs outputs → analysis → agreed checks → code/results → stage decision and next approved plan.

## Repository hygiene

- Keep raw datasets, databases, caches, and bulky generated files out of GitHub.
- Use `docs/` for compact research reports and tool documentation.
- Keep canonical project state current; remove superseded instructions rather than accumulating contradictory versions.
- Never claim execution from repository inspection alone.
