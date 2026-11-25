# Research Workflow Protocol

Last updated: 2026-11-25

## Mandatory stage loop

Every stage of the Data Science research cycle follows this sequence:

1. **Plan** — the Research Agent proposes the stage objective, scope, dependencies, methods, expected outputs, risks, and acceptance criteria.
2. **Approval** — the user reviews and approves the plan. No implementation begins before approval.
3. **Implementation** — implement the approved code in the GitHub repository. Keep experiments isolated, reproducible, and consistent with project boundaries.
4. **Compact evidence delivery** — write only the outputs needed for interpretation and reproducibility into the appropriate `docs/research/<project_or_stage>/` location (or an existing project-specific docs path where one is already established). Prefer concise Markdown summaries, tables, diagnostics, and small aggregates. Do not upload thousands of CSV rows or bulky raw/intermediate data. Keep raw datasets, databases, caches, and large generated files out of GitHub unless explicitly approved.
5. **Analysis** — inspect the committed code and compact outputs, distinguish facts from hypotheses, assess limitations, and deliver findings to the user.
6. **Test agreement** — propose necessary correctness, data-quality, statistical, robustness, and operational checks. Agree their scope with the user before adding material new tests or changing the experiment.
7. **Checks and results** — implement/run only the approved checks in an authorized environment. Record code, commands, outputs, and execution provenance. Never claim execution without actual runtime evidence.
8. **Stage decision** — summarize what passed, failed, remains uncertain, and whether the stage is complete, needs revision, or is blocked.
9. **Next stage** — propose the next stage using the previous stage's evidence and decisions. Obtain approval before implementation.

The user may explicitly combine or waive a step. Otherwise, this sequence is binding.

## Completion of the full research cycle

At the end of the full cycle, deliver a consolidated research report containing:
- Research question and final scope.
- Methods, data, assumptions, and validation protocol.
- Implemented code and reproducibility instructions.
- Key findings and evidence.
- Hypotheses supported, rejected, or unresolved.
- Limitations, failure modes, and known data gaps.
- Stage-by-stage test results and outstanding checks.
- Reusable knowledge/capabilities produced.
- Recommended next research questions, ranked with rationale, and a proposed plan.

## GitHub context architecture

Maintain separate, purpose-specific files under `llm_memory/research_agent/`:

- `01_ROLE_AND_RULES.md` — stable role, boundaries, permissions, and hard methodological constraints.
- `RESEARCH_WORKFLOW.md` — this mandatory stage protocol.
- `00_CUMULATIVE_KNOWLEDGE.md` — concise, reusable knowledge accumulated across completed research cycles; distinguish validated findings from hypotheses and project-specific observations.
- `RESEARCH_JOURNAL.md` — chronological record of decisions, stage transitions, corrections, and important events.
- Existing project-specific context files — detailed active project specifications and results, such as `06_ML_DIRECTION_FEATURE_RESEARCH.md`.
- `README.md` — navigation and source-of-truth index.
- `CHANGELOG.md` — concise record of context-structure and rule changes.

Avoid duplicating full content across files. Put each fact in its canonical home and link to it from other files. Update the index whenever files are added or reorganized.

## Context maintenance: current state, not accumulation

- Treat agent memory as an operational model of the current project, not a transcript or archive.
- When a decision, specification, status, or next step changes, rewrite the canonical section/file so it contains only the current valid instruction.
- Remove superseded instructions and stale next actions. Do not leave contradictory alternatives in active context.
- Keep the journal limited to concise, decision-relevant history: what changed, the current replacement, and why that matters. Do not append every discussion or duplicate the current specification.
- Keep cumulative knowledge genuinely reusable and current. Retire or replace claims when evidence changes; do not preserve obsolete hypotheses as active knowledge.
- Prefer deleting or rewriting stale text over adding explanatory layers that make the context longer.

## Evidence and storage discipline

- GitHub is the source of truth for committed code and Research Agent context.
- `docs/` contains compact, human-readable experiment outputs and tool documentation, not raw data dumps.
- Keep output size proportional to the decision being made. Prefer summaries and aggregate diagnostics over row-level exports.
- Record data snapshot/date, code revision, parameters, sample counts, and execution provenance.
- Label evidence as verified in GitHub, user-run/user-reported, code-inspected-not-run, or hypothesis.
- Repository inspection is not execution. Do not claim tests passed unless runtime output is available.
- Never edit user-owned daily reports.
- Do not change project code without explicit user authorization; this workflow approval authorizes only the implementation scope explicitly agreed for that stage.
