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

## Tool-building rule

Do not create a tool merely because a component has a name. First observe repeated friction in real allocation runs, then propose the smallest tool that removes that bottleneck. Preserve raw facts and source provenance; never let an LLM overwrite source data or deterministic calculations. No tool places orders.

## Possible future tools (not current priorities)

Only revisit when real workflow evidence justifies them:
- lightweight market-snapshot validator;
- news/disclosure capture and deduplication;
- fundamental fact normalization;
- Qwen prompt/evidence packet helper;
- allocation and constraint arithmetic checks.

These are candidates, not commitments or claims of implementation.