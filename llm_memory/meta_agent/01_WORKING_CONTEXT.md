# Meta-Agent Working Context

Last updated: 2026-11-23

## Source of truth and operating boundaries

- Main project repository: `dstark713-oss/pipeline`.
- GitHub is the source of truth for committed code and project context.
- The user runs Python locally in VS Code and supplies execution output for diagnosis.
- Never claim local runtime validation unless the user has supplied the result.
- The user explicitly authorizes code changes when they say to implement/build/commit a requested tool or script. Do not make unrelated code changes.
- Prefer complete runnable Python files over patch instructions.
- Every Python file must begin with comments containing its folder path and filename.
- Do not commit raw data, SQLite databases, Parquet datasets, CSV calculation outputs, logs, caches, or temporary files.

## Meta-agent boundary

The Meta-Agent maintains the multi-agent architecture, repository organization, agent roles, permissions, and shared operating conventions. It does not own the substantive research context of the Research Agent or the operating context of other specialist agents.

Research methodology, primitive definitions, scanner behavior, statistical evaluation, and interpretation rules belong in `llm_memory/research_agent/` and the relevant `docs/` documentation. Do not duplicate specialist-agent context here unless a cross-agent architectural rule genuinely requires it.
