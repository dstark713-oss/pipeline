# Sizing Agent Journal

## 2026-11-27 — Two-iteration mandate and first independent audit

### Capital mandate

- Total capital is divided into two fixed sleeves:
  - Aggressive Trading: 50%.
  - Conservative Investment: 50%.
- Sizing allocates positions only within the relevant sleeve.
- No silent transfer of capital between sleeves.
- Cash is a valid allocation inside either sleeve. A 50% sleeve mandate does not require 100% deployment of that sleeve.

### Mandatory two-iteration workflow

**Iteration 1 — independent challenge / falsification**

- Read both agent journals and the actual handoff artifacts.
- Challenge each conclusion logically before considering weights.
- Build deterministic Python checks and commit the scripts to the canonical repository.
- The user runs the scripts locally and returns compact console output.
- Never claim that a script has run until its output is returned and inspected.
- Never accept an agent's narrative or claimed validation on trust.
- If the data cannot test a claim, state the limitation rather than inventing a proxy as proof.

**Iteration 2 — allocation and position sizing**

- Starts only after Iteration 1 outputs have been reviewed.
- Quantify position sizes within each 50% sleeve.
- Consider expected return evidence, uncertainty, realized risk, co-movement / overlap, concentration, liquidity, implementation costs, short constraints, and the actual Risk Profile.
- Do not invent missing limits or portfolio facts.
- If essential constraints are missing, label numerical weights provisional or abstain.
- No order placement or autonomous portfolio changes.

### Journals and handoffs read

- `llm_memory/agents/aggressive_trading/journal.md`
- `llm_memory/agents/conservative_investment/JOURNAL.md`
- `llm_memory/agents/aggressive_trading/ROLE.md`
- `llm_memory/agents/conservative_investment/ROLE.md`
- `llm_memory/agents/shared/OPERATING_PROTOCOL.md`
- `llm_memory/agents/sizing/ROLE.md`
- `docs/aggressive_name_signals_report.md`

### Current handoff facts

**Aggressive Trading, snapshot 2026-11-26**

- Long: 10 primary candidates — CNRU, HYDR, SVCB, T, SMLT, DOMRF, MTSS, PHOR, VKCO, RTKM.
- Short: 4 conditional candidates — RNFT, FEES, SGZH, GAZP.
- Intended holding horizon: 10–20 sessions.
- Long selection: positive RS20 and top quintile of RS20 within the same RS5 quintile.
- Short selection: negative RS5 and RS20, both bottom quintiles; evidence weaker, regime-dependent, and borderline after multiple-testing adjustment.
- No target weights are supplied.
- The reported CSV artifact was not found in GitHub; the committed Markdown report is the readable source of the ticker list.
- Relative strength is not proof of positive absolute return. MTSS and PHOR have negative absolute 20D returns; SMLT and VKCO have high reported realized volatility.
- Short borrow, permission, and implementation have not been verified.

**Conservative Investment, journal 2026-11-26**

- User-confirmed portfolio posture recorded by the agent: 100% cash, superseding older T / GCHE / LQDT snapshots.
- No sector/company BUY thesis has been established.
- The documented next task is sector-first fundamental screening; the journal does not contain a completed positive sector screen or source-linked company financial analysis.
- TOP50 breadth diagnostics are mixed: the latest Q4 slice improved versus the trailing 120-session picture. These are descriptive price/return diagnostics, not proof of business fundamentals.
- Therefore the current no-deployment posture is consistent with the absence of verified fundamental evidence, but is not proven optimal by price-only data.

### Iteration 1 artifact

Committed:
- `scripts/one_use/sizing_independent_audit/run_sizing_audit.py`

Purpose:
1. Rebuild historical Long / Short candidates from the point-in-time TOP50 panel using the documented RS5 / RS20 selection logic.
2. Test 10- and 20-session forward cohort returns after the stated 15 bps round-trip cost.
3. Require complete intervening session bars; no forward fill or gap bridging.
4. Report long excess return against same-date PIT equal-weight cross-section and short absolute P&L.
5. Reconcile latest independently rebuilt candidate lists against the 26-Nov handoff.
6. Recalculate Conservative breadth, equal-weight return, median return, and top-five positive contribution concentration for full, trailing 120/60/20-session, and 2026 Q4 windows.
7. Explicitly identify that the price-only panel has no sector/fundamental evidence fields.

Important limitations:
- Historical signal cohort means are not a fully executable portfolio backtest; signals overlap.
- The stated 15 bps is a simple round-trip cost assumption; turnover, borrow, slippage, capacity, and financing are not fully modeled.
- The reconstruction's RS definition must be reconciled with the signal agent's exact benchmark and feature construction. A low ticker overlap is a stop condition, not a reason to silently adjust the script.
- Conservative price-only diagnostics cannot falsify or validate company fundamentals. They can only challenge market-participation claims.
- The script has been committed but has NOT been executed by the user or independently validated against local output yet.

### Current status

- Iteration 1: script committed; awaiting user's local run and compact console output.
- Iteration 2: NOT STARTED.
- No position weights or allocation proposal are issued at this stage.
- Current verified handoff posture is no established Conservative BUY thesis; Aggressive candidate list remains unvalidated by Sizing.
- The 50% / 50% sleeve mandate remains fixed.


## 2026-11-27 — User correction and final Long audit iteration

### Correction to Conservative interpretation

- User clarified that Conservative's 100% cash is its actual decision, while its names are candidates for further research only.
- The price-only TOP50 audit was never intended to prove or disprove fundamentals; the panel contains no fundamental fields.
- The Conservative agent's current output is therefore role-consistent. Do not frame the missing fundamental columns as a failure of its current decision.
- Future challenge of Conservative must inspect sector-first and company-level fundamental reasoning, source quality, accounting consistency, valuation, and explicit falsification. No quantitative fundamental confirmation is currently available.

### First audit output received

- Panel as-of 2026-11-26; 5,491 sessions; 214 tickers; PIT guard passed; 15 bps RT assumption.
- Long 10-session: mean net +0.41%, median -0.04%, hit 49.6%, mean excess +0.23%, positive-year fraction 54.5%.
- Long 20-session: mean net +0.98%, median +0.25%, hit 51.2%, mean excess +0.42%, positive-year fraction 59.1%.
- Short results negative on mean net and excess at both horizons; short remains excluded from sizing absent materially different evidence and borrow/permission checks.
- Reconstructed latest Long candidates 12 with 8/10 overlap against the reported list. This is a material but not complete reproducibility match.
- Interpretation: Long survives as a candidate hypothesis but is not yet demonstrated as robust, independent, or executable alpha.

### Final Long audit script

Committed:
- `scripts/one_use/sizing_independent_audit/audit_long_final.py`

Checks:
1. Reconstruct the Long cohort from PIT TOP50 using positive RS20 and top-quintile RS20 within the same RS5 quintile.
2. Test 10- and 20-session forward returns at 15, 30, and 50 bps round-trip costs.
3. Calculate Newey-West/HAC uncertainty on the daily equal-weight signal-cohort return series, using horizon-minus-one lags for overlapping forward windows; include confidence intervals for absolute and benchmark-excess returns.
4. Report positive-year fraction by cost scenario.
5. Report historical per-ticker signal performance for the names in the reported packet / independently reconstructed latest list.
6. Measure how concentrated positive equal-weight P&L contributions are among the strongest ticker contributors.
7. Produce a latest name-level risk/liquidity snapshot using fixed last-20 / last-60 global-session windows, plus a 60-session pairwise return-correlation matrix for the reported names.
8. Preserve explicit limitations: HAC is asymptotic; the cohort test is not a fully executable portfolio simulation; ticker-level history is conditional on the reconstructed signal; 60-session correlations are unstable estimates; no weights are produced.

Commits:
- Initial final audit: `dadebbc58456897d3795179737474b1fc22a6f36`
- Correct candidate positive-year calculation: `8933796e2cf8a742a371ed64776d0afc8112b0a7`
- Correct fixed-session volatility/liquidity windows: `defb8cc3606651f62092706dcc4114940e0f3296`

### Current stage status

- Iteration 1: final Long audit script committed; awaiting user's local run and compact output.
- Iteration 2 (name selection and sizing): not yet started; begins immediately after final Long audit output is reviewed.
- User explicitly authorized zero weights for candidates that do not merit capital; the reported ten names are not a mandatory buy list.
- Fixed capital mandate remains 50% Aggressive / 50% Conservative. Cash is permitted inside either sleeve. No cross-sleeve transfer.
- No live positions or orders changed.
