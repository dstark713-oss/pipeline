# Trading Agent Tool Registry

Last updated: 2026-11-23

This registry records what is present in the repository versus what the daily process still needs. A tool is not considered operational merely because a path is listed.

## Existing deterministic tools

| Tool | Path | Purpose | Status / caveat |
|---|---|---|---|
| Daily MOEX refresh | `scripts/dataset/fresh/refresh_pipeline.py` | Append new raw MOEX bars; rebuild adjusted DB and PIT TOP50 panel | Code inspected; user-run validation required. No historical onboarding for pairs with no raw rows. |
| Feature builder | `scripts/experiments/primitives/05_build_primitive_features.py` | Build primitive feature frame | Referenced by screener docs; inspect exact current prerequisites and output path before first run. |
| Primitive screener | `scripts/tools/01_primitive_screener.py` | Current PIT TOP50 instrument-state snapshot and separate breadth report | Read-only; does not generate actions or weights. |
| Screener specification | `docs/tools/01_primitive_screener.md` | Definitions, output fields, interpretation and limitations | Existing source of truth for screener use. |

## Current local output contract

- `data/interim/fresh/refresh_summary.json`
- `data/interim/fresh/refresh_errors.csv`
- `data/processed/top50/top50_panel.parquet`
- `data/interim/primitive_research/primitive_features.parquet`
- `data/interim/screener/latest_primitive_snapshot.csv`
- `data/interim/screener/latest_market_breadth.csv`

These are local artifacts and are not expected to be committed to GitHub.

## Missing or unverified tool families

| Tool family | Required capability | State |
|---|---|---|
| Portfolio snapshot reader | Read positions, quantity, market value, cash, cost basis, currency, account and as-of timestamp from a user-approved export | Missing from visible repository inventory; schema/access to establish. |
| News collector | Search issuer, sector, macro, regulator and corporate-event news; deduplicate and preserve source/time | No dedicated committed tool identified in the inspected tree. |
| Disclosure/fundamental collector | Retrieve issuer reports, MOEX disclosures, dividend/corporate-action notices and normalized financial facts | No dedicated committed tool identified in the inspected tree. |
| Semantic event store | Normalize events, entities, novelty, impact channel, horizon, confidence and source provenance | Not implemented in inspected tree. |
| Qwen API adapter | Submit evidence packet to Qwen only; persist prompt, response, model/version and timestamp | Not identified in inspected tree. |
| Allocation engine | Combine existing positions, constraints, deterministic state and reviewed evidence into target weights | Not identified in inspected tree. |
| Daily run manifest | Track input dates, tool versions, source links, failures, outputs and decision ID | Not identified in inspected tree. |

"Not identified" means absent from the inspected repository paths, not proof that the user has no separate local implementation or service.

## Tool design principles

1. Each tool has a narrow responsibility and a documented input/output schema.
2. Raw source capture is separate from normalization and interpretation.
3. Every record preserves source URL, source name, publication/event timestamp, retrieval timestamp, issuer/entity mapping, and raw text or stable source reference where legally and technically appropriate.
4. Collection is idempotent; repeated runs update retrieval metadata but do not create duplicate events.
5. Store local generated data outside Git. Commit code, schemas, deterministic tests, and concise documentation only.
6. Use explicit freshness thresholds and fail closed when critical data is stale.
7. Never let an LLM silently overwrite raw facts or deterministic calculations.
8. Every allocation must be reproducible from a run manifest and saved evidence packet.
9. API autonomy requires credentials/configuration supplied by the user, tested rate limits, retries, caching, error handling, and budget controls.
10. No tool places orders.

## Proposed implementation order

1. Portfolio snapshot contract and read-only validator.
2. Deterministic daily run manifest / freshness gate.
3. News and official-disclosure ingestion with deduplication.
4. Fundamental facts normalization for the actual portfolio universe.
5. Semantic event extraction and issuer-impact mapping.
6. Qwen-only review adapter.
7. Allocation synthesis / constraint checker.
8. End-to-end orchestration and API-mode acceptance tests.

This order deliberately starts with the portfolio and data contracts. Building a clever news agent before knowing what the portfolio owns is a familiar way to automate irrelevance.
