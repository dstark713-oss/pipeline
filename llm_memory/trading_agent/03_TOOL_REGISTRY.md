# Trading Agent Tool Registry

Last updated: 2026-11-23

The current objective is to train the agent's allocation reasoning through manual daily cycles. Tooling should support that process, not become the project itself.

## Existing local market tools

| Tool | Path | Purpose | Current use |
|---|---|---|---|
| Daily MOEX refresh | `scripts/dataset/fresh/refresh_pipeline.py` | Refresh local MOEX observations and rebuild derived data | User runs when needed and shares outputs/status. |
| Feature builder | `scripts/experiments/primitives/05_build_primitive_features.py` | Build primitive feature frame | User runs when needed and shares outputs/status. |
| Primitive screener | `scripts/tools/01_primitive_screener.py` | Instrument state and market breadth snapshot | User runs when needed and shares outputs/status. |
| Screener specification | `docs/tools/01_primitive_screener.md` | Definitions and limitations | Reference for interpretation. |

The screener's descriptive primitives include `drawdown_60`, `zscore_sma20_20`, and `realized_vol_60`; market context includes `breadth_change_5` and `breadth_sma20`. It is not a buy/sell or allocation engine.

## Manual inputs and agent responsibilities

| Component | Current implementation |
|---|---|
| Portfolio Reader | Simple allocation ledger in Trading Agent memory, updated from user-provided snapshots and agreed decisions. |
| Daily Market Snapshot | User supplies local outputs; agent requests exact missing outputs. |
| News & Fundamentals | Agent researches public internet sources during each allocation run. |
| Semantic Engine | Agent's own LLM reasoning over sourced facts, events, and issuer impact. No separate service required now. |
| Qwen Reviewer | User runs Qwen and returns its response; no direct API adapter assumed. |
| Allocation Engine | Agent's reasoning and recommendation, documented in the research journal. |
| API Orchestration | Deferred until the manual process is proven through repeated market cycles. |

## One-use research scripts

Planned directory: `scripts/one_use/`. It may be created when the first concrete script is needed; do not add empty scaffolding or speculative utilities.

A one-use script is appropriate when:
- the allocation decision depends on data not exposed by existing tools;
- a local database/file/API can answer a specific research question;
- a focused extraction, validation, or calculation is more reliable than manual copying.

Required properties:
- complete runnable script with repository-relative path in its header;
- narrow stated research question and explanation of decision relevance;
- read-only by default, no writes to production databases or canonical datasets;
- bounded inputs/time range and explicit output path/schema;
- useful validation and clear failure messages;
- user receives exact run command and requested output artifact;
- script remains unverified until the user returns execution output.

The user may run the script locally after receiving it in chat or pull it from GitHub. When Codex/Python access is later available, the agent may inspect and analyze accessible local data directly within granted permissions.

## Tool-building rule

Do not create a tool merely because a component has a name. First observe a concrete information gap in a real allocation run, then choose the smallest method: internet research, existing local output, one-use script, or (only if the need recurs) a permanent tool. No tool places orders.