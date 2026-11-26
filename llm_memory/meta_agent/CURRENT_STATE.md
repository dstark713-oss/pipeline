# Meta-Agent — Current Project State

Last updated: 2026-11-27

## Canonical repository state

- Repository: `dstark713-oss/pipeline`.
- Branch: `main`.
- Commit reviewed before this architecture update: `96a84dcbb17127c82aff3bc167bd3b40c80ab3e4`.
- Current implementation is a MOEX-focused research/data foundation, not a completed trading platform.

## Current research state (repository-verified)

- MOEX ISS data collection, incremental refresh, adjusted datasets and PIT TOP50 panel exist.
- Research Agent memory and staged research workflow exist under `llm_memory/research_agent/`.
- EDA2 result folders are committed through block 5.
- Block 5 report: 5,490 panel dates, 214 securities and 196,663 return observations; rolling scale distributions and cross-period relative-scale stability are described. The report explicitly makes no GARCH, forecasting, ML, IC, feature-selection or trading claims.
- The Research Agent's own journal is the source for chronological scientific decisions. Its latest committed entry predates some current EDA2 results; do not infer missing scientific status from project-level memory.
- The user's `daily_report.txt` is user-owned and must remain unmodified.

## Architecture decision — 2026-11-27

The previous conversational trading-agent pilot is retired.

Active responsibilities:
1. **Meta-Agent / Portfolio Steward — ChatGPT:** research-process governance, model/version trust tracking, conditional model preference, sizing and portfolio oversight across two sleeves, and governance of the Investment Agent.
2. **Research Agent:** research, experiments, model development, validation and scientific conclusions. Its underlying LLM is not permanently fixed; model quality will be evaluated from evidence.
3. **Investment Agent — ChatGPT:** separate sector/company fundamental investment process, governed by Meta-Agent.

Retired: Aggressive Trading LLM, conversational Signal LLM, separate Sizing LLM and the former shared three-agent protocol. The former Conservative Investment role and journal have been migrated into Meta-Agent memory.

## Capital architecture

- Strategic allocation: 50% model-driven trading sleeve / 50% investment sleeve.
- This is a split between mandates, not a requirement to fully deploy either sleeve.
- Cash is a valid state when no eligible model signal or sufficiently evidenced investment opportunity exists.
- Last explicit portfolio snapshot in the Investment Agent journal: 100% cash, no open positions, dated 2026-11-26. This is not assumed current without reconfirmation.
- Real portfolio changes remain manual and require user approval.

## Model trust

- No verified model registry with accumulated live track records exists yet.
- `MODEL_REGISTER.md` defines the evidence fields and comparison policy.
- Trust is multidimensional; no arbitrary scalar score or fixed model ranking is used.
- Model preferences must be conditional on target, horizon, universe, data, market state and evidence quality.

## Current governance priorities

1. Keep the Research Agent focused on substantive research and reproducible model development; avoid spending hours on unnecessary conversational orchestration.
2. Maintain clean research-to-model handoffs with version, data snapshot, horizon, validation status and uncertainty.
3. Accumulate model evidence across walk-forward, shadow/paper and live stages without conflating them.
4. Keep the Investment Agent sector-first and evidence-led.
5. Review both sleeves together while preserving the 50/50 strategic capital split.
6. Do not implement automated execution or alter user-owned risk limits.

## Evidence and scope boundaries

- Repository inspection is not runtime execution.
- Research methods and scientific conclusions remain Research Agent-owned.
- Meta-Agent may correct role/process instructions and governance records, not rewrite research results.
- No broker API or automatic position changes are authorized.
