# Meta-Agent: Current Project State

Last updated: 2026-11-26

## Repository

- Working repository: `dstark713-oss/pipeline`.
- Branch: `main`.
- Latest repository commit inspected before this context update: `0e1008f231e71aa131cf303e1343304d4cd11833`.
- Repository README describes a MOEX-focused research and data infrastructure, not a completed multi-agent trading platform.

## Current implementation (repository-verified)

The root README documents:
- MOEX ISS data collection and incremental refresh;
- historical universe and dataset construction;
- adjusted datasets and point-in-time panels;
- isolated statistical and ML experiments;
- research-agent context under `llm_memory/research_agent/`.

The repository README records Log Returns as a completed base representation and Rolling Statistical Moments as closed on 2026-11-25. These are Research Agent facts; Meta-Agent does not reopen or reinterpret them.

## Target roles (user-approved)

- Meta-Agent — ChatGPT.
- Quant Research — Qwen primary researcher plus independent GPT critique.
- Sizing — ChatGPT, backed by deterministic Python validation.
- Aggressive Trading — Qwen.
- Conservative Investment — ChatGPT.

The five functional roles map to three top-level system components: Signal LLM, Sizing LLM, and Meta-Agent. Python Risk Engine is a deterministic hard-control layer.

## Important boundaries

- Research methods, calculations and conclusions are owned by Quant Research.
- Meta-Agent owns architecture, agent memory, repository governance and lifecycle.
- ChatGPT is the primary code author; Qwen is not authorized to independently modify the working repository.
- No broker integration, automatic order submission or automatic changes to real positions.
- No invented Risk Profile limits.
- The current MOEX research implementation must not be described as a completed multi-asset platform.

## Open architecture work

- Formalize typed contracts between research outputs, signal decisions, sizing proposals and deterministic validation.
- Implement the Python Risk Engine only after its inputs, outputs and user-approved Risk Profile interface are specified.
- Define versioned agent configuration and audit records.
- Build shadow evaluation, promotion and rollback controls.
- Expand beyond MOEX only when a concrete requirement and data-source contract exist.

## Research handoff

The Research Agent owns the active EDA/research stage and its next-step decisions. Meta-Agent checks process integrity and handoff readiness only. Any stale research-specific context must be resolved by its owner, not silently rewritten here.


## Outstanding owner-level memory issue

During the architecture review, the Research Agent's `README.md`, `05_NEXT_STEPS.md`, and `06_ML_DIRECTION_FEATURE_RESEARCH.md` still described EDA v2 as awaiting approval / implementation, while the repository contains committed EDA2 block 5 artifacts. This is a stale status conflict, not a reason for Meta-Agent to infer the next research stage.

Ownership: Quant Research / Research Agent (Qwen-led, GPT critique). Meta-Agent must route this discrepancy to the research owner and verify that the owner synchronizes its context. Do not edit research methods, reports, calculations, or next-stage decisions from this role.
