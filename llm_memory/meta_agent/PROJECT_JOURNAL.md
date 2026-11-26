# Project Journal — LLM-maintained

**Last updated:** 2026-11-27  
**Maintainer:** Meta-Agent (ChatGPT)  
**Repository:** `dstark713-oss/pipeline`, branch `main`

This journal records project-level architecture, model governance, portfolio-process decisions and operational corrections. It is maintained by the LLM. It is separate from the user's personal `daily_report.txt`, which remains user-owned and must never be edited by the LLM.

---

## 2026-11-27 — Retire conversational trading-agent architecture

### User decision

The three-agent conversational trading scheme is retired as the active operating architecture. The concept remains useful, but the observed workflow took approximately 2.5 hours even with automated script writing. That overhead is not justified when the time is better spent on research and model development.

### New architecture

- **Research Agent:** conducts research, designs experiments, writes/validates models and returns model outputs with evidence.
- **Meta-Agent / Portfolio Steward (ChatGPT):** monitors the Research Agent's process, tracks model/version evidence and trust, compares models when several exist, receives model outputs, proposes sizing and oversees both real portfolio sleeves.
- **Investment Agent (ChatGPT):** retained as a separate fundamental investment process and portfolio sleeve.

Retired roles: Aggressive Trading LLM, conversational Signal LLM, separate Sizing LLM and the shared three-agent trading protocol. The former Conservative Investment role and journal were migrated into Meta-Agent memory.

### Capital policy

The strategic capital split remains:
- 50% model-driven trading sleeve;
- 50% investment sleeve.

The split is between mandates, not a target exposure. Either sleeve may remain partly or fully in cash when there is no justified opportunity. No forced deployment.

### Signal and sizing authority

- The validated model is the source of trading signals.
- ChatGPT must not generate a competing BUY/SELL signal or replace the model's output.
- ChatGPT is responsible for interpreting model provenance, validity and uncertainty in portfolio context and proposing sizing.
- The Investment Agent's fundamental conclusions remain separate from model outputs.
- The user manually approves all real portfolio changes. No broker API or autonomous execution.

### Model trust and preference

Trust is recorded as a multidimensional evidence profile, not a made-up scalar score. Compare models by task, horizon, universe, data, walk-forward/out-of-sample robustness, calibration, coverage, uncertainty, costs where permitted, shadow evidence and live outcomes. Preferences must be conditional and traceable. No production promotion without explicit approval.

### Governance boundaries

The Meta-Agent monitors research scope, process, provenance, reproducibility, validation and handoff quality. It may correct the Research Agent's and Investment Agent's operating instructions when process errors are observed. It does not take over scientific ownership or silently rewrite research methods, calculations or conclusions.

### Source review completed

- User-owned `daily_report.txt` was read and left unchanged.
- Research Agent `RESEARCH_JOURNAL.md`, `RESEARCH_WORKFLOW.md`, role instructions and current research context were reviewed.
- EDA2 block 5 report was read: 5,490 panel dates, 214 securities and 196,663 return observations. The report documents rolling scale distributions and cross-period relative-scale stability; it explicitly makes no forecasting, GARCH, IC, feature-selection or trading claim.
- Conservative Investment `JOURNAL.md` was read. Its 2026-11-26 snapshot records 100% cash and no open positions; this is historical until reconfirmed. Its sector-first process correction is retained as binding.
- Repository tree was inspected. The previous `docs/PROJECT_ROADMAP.md` was absent on current `main`; it is recreated as part of this governance update.

### Evidence and limitations

- Repository state and committed research report: GitHub-verified.
- Portfolio state: last recorded in Investment Agent journal on 2026-11-26; not reconfirmed on 2026-11-27.
- No production-eligible model is currently registered in `MODEL_REGISTER.md`.
- No model trust ranking is claimed.
- No new research experiment or portfolio calculation was run as part of this architecture change.

### Next governance actions

1. Continue substantive research; avoid rebuilding the retired conversational chain.
2. Require model outputs to include model/version, data/as-of, universe, target/horizon, signal, uncertainty and validation artifact.
3. Populate model evidence records as actual results arrive.
4. Review model preferences only when comparable evidence exists.
5. Receive current portfolio state before any numerical sizing proposal.
6. Review Investment Agent work against the sector-first process and update instructions only when needed.


### Open process discrepancy found during source review

The committed EDA2 block 5 report exists under `docs/research/eda2/results/block_05/`, but `docs/research/eda2/WORKING_CONTEXT.md` still says the local run is pending and that the user should run/publish the outputs. The report's provenance and the working-context status need to be reconciled by the Research Agent. Meta-Agent does not infer a runtime execution claim beyond the committed report and does not rewrite the research interpretation.
