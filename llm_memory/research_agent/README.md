# Research Agent Memory

Last updated: 2026-11-23

This directory is the persistent working context for the Research Agent in `dstark713-oss/pipeline`. It is not user-facing product documentation. Keep it factual, compact enough to navigate, and explicit about uncertainty.

## Source of truth

- GitHub repository: [dstark713-oss/pipeline](https://github.com/dstark713-oss/pipeline)
- Current branch: `main`
- Project code and committed research artifacts are authoritative for what exists.
- This memory records decisions, rationale, status, observations, hypotheses, and next steps that are not obvious from code.
- Local `data/` is intentionally not committed. Its latest user-reported state is recorded here and must not be mistaken for a live inspection of local files.

## Read order

1. [Role and operating rules](01_ROLE_AND_RULES.md)
2. [Dataset pipeline state](02_DATASET_PIPELINE.md)
3. [Primitive research](03_PRIMITIVE_RESEARCH.md)
4. [Refresh mechanism](04_REFRESH_MECHANISM.md)
5. [Next steps and open risks](05_NEXT_STEPS.md)
6. [Research journal](RESEARCH_JOURNAL.md)
7. [Change log](CHANGELOG.md)

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
- Keep chronological notes in `CHANGELOG.md`.
- Record exact paths, command lines, commit SHAs, data dates, and key output counts where available.
- Distinguish the current state from intended future architecture.
- Do not copy raw datasets, SQLite databases, Parquet files, logs, or bulky generated reports into GitHub memory.
- Do not create duplicate instructions in `docs/`; that directory is reserved for tool instructions. The only current exception is `docs/tools/00_refresh_ds.md`.

## Project boundary

The immediate research problem is to build and validate a compact set of interpretable instrument-state primitives from the point-in-time TOP50 dataset. The primitives are information inputs for later agent reasoning, not standalone trading strategies and not an automatic trade/weight generator.

The read-only production screener now exists at scripts/tools/01_primitive_screener.py. Its downstream specification is in docs/tools/01_primitive_screener.md. It exposes three instrument-level primitives and a separate two-value breadth context. The screener is descriptive only; it does not choose trades or weights.
