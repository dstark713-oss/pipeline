# Research Agent Memory

Last updated: 2026-11-25

Persistent working context for the Research Agent in `dstark713-oss/pipeline`. This is operational context, not a transcript.

## Source of truth

- Repository: [dstark713-oss/pipeline](https://github.com/dstark713-oss/pipeline), branch `main`.
- Committed code and research artifacts define what exists.
- Local `data/` is not committed. User-reported local state must not be mistaken for live inspection.
- Evidence must be labeled as verified in GitHub, user-run/user-reported, code-inspected-not-run, or hypothesis.

## Read order

1. [Role and operating rules](01_ROLE_AND_RULES.md)
2. [Research workflow protocol](RESEARCH_WORKFLOW.md)
3. [Cumulative research knowledge](00_CUMULATIVE_KNOWLEDGE.md)
4. [Dataset pipeline state](02_DATASET_PIPELINE.md)
5. [Primitive research](03_PRIMITIVE_RESEARCH.md)
6. [Refresh mechanism](04_REFRESH_MECHANISM.md)
7. [Current stage and next steps](05_NEXT_STEPS.md)
8. [ML research and EDA specification](06_ML_DIRECTION_FEATURE_RESEARCH.md)
9. [Research journal](RESEARCH_JOURNAL.md)
10. [Change log](CHANGELOG.md)

## Current project

The active research stage is descriptive EDA on the PIT TOP50 panel. The approved specification is `docs/research/eda/EDA_SPEC.md`; implementation is in `scripts/experiments/ml_1/eda/`. Horizons 1/5/20 are descriptive comparisons only. No target, model, or prediction horizon has been selected.

The first primitive research cycle and market-state screener hypothesis are closed. The screener is the first runtime analytical tool, not the boundary of future research.

There is no internal fundamental-data dataset or pipeline. External news, market semantics, company context, and fundamental information require source and temporal provenance; present-day web information is not point-in-time historical evidence.

## Mandatory operating protocol

Every stage follows `RESEARCH_WORKFLOW.md`: plan → user approval → implementation → compact docs outputs → analysis → agreed checks → code/results → stage decision and next approved plan.

## Repository hygiene

- Keep raw datasets, databases, caches, and bulky generated files out of GitHub.
- Use `docs/` for compact research reports and tool documentation.
- Keep canonical project state current; remove superseded instructions rather than accumulating contradictory versions.
- Never claim execution from repository inspection alone.
