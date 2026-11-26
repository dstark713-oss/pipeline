# Meta-Agent Memory

Last updated: 2026-11-26

Persistent operating memory for the Meta-Agent of `dstark713-oss/pipeline`. This is a compact operational context, not a chat transcript.

## Canonical sources

1. [Master Specification](../../docs/architecture/MASTER_SPECIFICATION.md) — target system architecture, role boundaries, authority and safety constraints.
2. [Project Roadmap](../../docs/PROJECT_ROADMAP.md) — dependency-ordered transition from current implementation to target capabilities.
3. [Meta-Agent Role and Rules](ROLE_AND_RULES.md) — mandate, permissions and prohibited scope.
4. [Current Project State](CURRENT_STATE.md) — verified repository state and open governance work.

## Repository boundary

- Working repository: `dstark713-oss/pipeline`, branch `main`.
- `research1` and `research2` are reference-only and are not work targets.
- The Meta-Agent's persistent memory belongs here, under `llm_memory/meta_agent/`.
- Research-specific methodology, calculations, reports and conclusions belong to the Research Agent's context and research documentation. Do not copy or reinterpret them here.

## Operating rule

Before acting, read this index, the role rules, current state, and the relevant canonical specification. Update this memory when a user decision changes architecture, permissions, ownership, or project-level status. Keep it concise and link to detailed sources rather than duplicating them.
