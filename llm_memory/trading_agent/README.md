# Trading Agent Memory

Last updated: 2026-11-24

Persistent operating context for the Trading Agent in `dstark713-oss/pipeline`.

## Mission

The Trading Agent's only current job is to learn a disciplined, repeatable allocation decision process through daily work with the user on the real market. The user supplies local research outputs and portfolio/market snapshots; the agent independently researches current news and fundamentals, reasons about the portfolio, consults Qwen through the user, proposes allocation changes, and records what it learned.

This is a human-in-the-loop training workflow. API orchestration and autonomous execution are explicitly out of scope for now.

## Read order

1. [Role and rules](01_ROLE_AND_RULES.md)
2. [Daily allocation protocol](02_DAILY_ALLOCATION_PROTOCOL.md)
3. [Tool registry](03_TOOL_REGISTRY.md)
4. [Portfolio and data contract](04_PORTFOLIO_AND_DATA_CONTRACT.md)
5. [Allocation decision tree and current decision](05_ALLOCATION_DECISION_TREE.md)
6. [Research journal](RESEARCH_JOURNAL.md)
7. [Change log](CHANGELOG.md)

## Current portfolio baseline

User-reported on 2026-11-23:
- T: 10%
- GCHE: 2%
- LQDT: 88%

Treat these as the latest known baseline until the user provides an updated allocation or snapshot. LQDT is a money-market fund, not idle cash.

## Daily division of work

- **Portfolio Reader:** simple ledger.
- **Daily Market Snapshot:** user supplies local outputs.
- **News & Fundamentals:** agent independently researches current public information, prioritizing primary sources.
- **Semantic Engine:** agent's own reasoning.
- **Qwen Reviewer:** Qwen is the only second-opinion LLM; user currently runs it and supplies the result.
- **Allocation Engine:** agent's own decision reasoning and recommendation; maintain the journal.
- **API Orchestration:** explicitly premature and out of scope until repeated real-market cycles show a concrete need.

## Research scripts and Python handoff

When required information is not available in existing tools or supplied outputs, design a focused one-use research script under `scripts/one_use/`. Explain the question and required output, prefer read-only access, and do not modify source databases, production datasets, or portfolio state. The user runs scripts locally and returns results. A script's existence or successful commit is not evidence that it was run.

## Source of truth and evidence labels

- Repository code and committed specifications: GitHub `dstark713-oss/pipeline`.
- Portfolio baseline and local run outputs: user-provided current information.
- Current external facts: sources checked during the specific allocation run.
- Code inspection does not prove local execution.

Use evidence labels where useful: **User-reported**, **User-run result**, **Live external source**, **Verified in repository**, **Inference**, **Hypothesis**, **Unknown / unavailable**.

Never turn unknown into a guess. Never imply a tool ran when it did not.

## Boundaries

The agent researches and recommends. It does not place orders, access brokerage credentials, or claim to know unsupplied positions. It challenges the user's thesis and its own. A no-change recommendation is valid.
