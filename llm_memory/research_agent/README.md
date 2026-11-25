# Research Agent Memory

Last updated: 2026-11-26

Persistent working context for the Research Agent in `dstark713-oss/pipeline`. This is operational context, not a transcript.

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
8. [ML research and EDA findings](06_ML_DIRECTION_FEATURE_RESEARCH.md)
9. [Research journal](RESEARCH_JOURNAL.md)
10. [Change log](CHANGELOG.md)

## Current project

The active stage is targeted diagnostic validation after the completed PIT TOP50 EDA run. Read:
- Approved scope: `docs/research/eda/EDA_SPEC.md`
- Generated results: `docs/research/eda/EDA_REPORT.md`
- Research interpretation and proposed checks: `docs/research/eda/EDA_ANALYSIS.md`
- Implementation: `scripts/experiments/ml_1/eda/`

No target, label, model, feature family, or prediction horizon has been selected. The +1/+5/+20 horizons are descriptive only.

The first primitive research cycle and market-state screener hypothesis are closed. The screener is the first runtime analytical tool, not the boundary of future research.

There is no internal fundamental-data dataset or pipeline. External news, market semantics, company context, and fundamental information require source and temporal provenance; present-day web information is not point-in-time historical evidence.

## Mandatory operating protocol

Every stage follows `RESEARCH_WORKFLOW.md`: plan → user approval → implementation → compact docs outputs → analysis → agreed checks → code/results → stage decision and next approved plan.

## Repository hygiene

- Keep raw datasets, databases, caches, and bulky generated files out of GitHub.
- Use `docs/` for compact research reports and tool documentation.
- Keep canonical project state current; remove superseded instructions rather than accumulating contradictory versions.
- Never claim execution from repository inspection alone.
