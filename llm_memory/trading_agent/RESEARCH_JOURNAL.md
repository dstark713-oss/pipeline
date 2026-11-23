# Trading Agent Research Journal

Chronological log of role setup, daily allocation investigations, tool audits, decisions, and unresolved risks. This is the Trading Agent's journal and is separate from the user's `daily_report.txt` and the Research Agent's journal.

## 2026-11-23 | Agent initialization and repository reconnaissance

### User mandate

The user defined a daily workflow triggered by "Аллокация на сегодня". The Trading Agent is to:
- identify and request required local tool runs;
- collect and analyze news;
- review fundamentals;
- perform semantic/contextual analysis;
- request a second opinion from Qwen only;
- synthesize and propose portfolio allocation;
- maintain its own persistent context and research journal;
- work toward future API-driven autonomy.

The user currently orchestrates the workflow and shares tool outputs. Decisions remain collaborative. No autonomous order execution is authorized.

### Repository reconnaissance

Inspected the repository root, `llm_memory/`, existing specialist-agent memories, the deterministic screener specification, the dataset refresh implementation, and the relevant script directory inventories.

Existing deterministic stack:
- `scripts/dataset/fresh/refresh_pipeline.py`
- `scripts/experiments/primitives/05_build_primitive_features.py` (referenced by screener documentation; execution not verified)
- `scripts/tools/01_primitive_screener.py`
- `docs/tools/01_primitive_screener.md`

The screener exposes:
- instrument state: `drawdown_60`, `zscore_sma20_20`, `realized_vol_60`;
- separate market context: `breadth_change_5`, `breadth_sma20`.

It is descriptive/read-only and does not generate buy/sell signals or portfolio weights.

The refresh script appends raw observations and rebuilds adjusted data and PIT TOP50. Its current documented/code-inspected limitations include no onboarding/backfill for SECID/board pairs without existing raw rows, a calendar-yesterday cutoff, and checkpoint advancement after an empty response. Local runtime status is not established by repository inspection.

### Important gaps

No dedicated portfolio snapshot reader, news collector, fundamental/disclosure normalizer, semantic event store, Qwen adapter, allocation engine, or daily run manifest was identified in the inspected repository paths. These may exist outside this repository; do not claim they do not exist globally.

The current portfolio holdings, cash, account constraints, and position-level snapshot were not present in the inspected repository content. Precise target weights cannot be responsibly calculated until the user provides a portfolio export or a supported read-only source.

### Initial architecture decision

Build the agent as a layered decision-support workflow:
1. portfolio and constraints;
2. deterministic market-state snapshot;
3. news and official disclosures;
4. normalized fundamental facts;
5. semantic event interpretation;
6. Qwen-only adversarial review;
7. constrained allocation synthesis;
8. run manifest, decision report, and journal.

Keep deterministic facts separate from LLM interpretation. Keep raw/local outputs outside Git. No trade execution.

### Next action

Establish the portfolio snapshot format and current holdings source. Then map existing local tools and implement the first read-only portfolio validator / daily run manifest only after the user confirms the available export and authorizes code implementation.

### Evidence status

- Repository paths and committed docs: inspected in GitHub.
- Local Python execution: not performed.
- Current local database freshness: unknown.
- Current portfolio holdings/weights/cash: not supplied in this inspection.
- Qwen API availability/credentials: not established.
