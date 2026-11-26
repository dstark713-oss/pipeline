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

- Final audit clarification: HAC inference is on the date-level equal-weight mean of overlapping h-session cohort forward returns (zero on dates with no eligible cohort), not a marked-to-market daily portfolio return stream. This avoids overstating what the cohort test estimates.
- Final script clarification commit: `09fbbece29e592118829ff524d1d8cd860a39688`.
- Console output includes the reported ten names' historical signal stats and a compact 60-session correlation summary so the next sizing turn can work from one pasted output; detailed per-name CSVs and the full matrix are also saved locally.
- Final console-output commit: `c8cd81ddf1c910870754ad9f5904f4b4c6794663`.
- Final console column-name correction commit: `d4d0561285bd49a7fe1ddde0757439d5557cc510`.


## 2026-11-27 — Final Long audit reviewed; Iteration 1 closed; provisional Iteration 2

### User clarification

- Conservative's 100% cash is the decision, and its names are research candidates only. The previous price-only audit is not a test of Conservative's fundamental reasoning. Future challenge is based on actual sector/company fundamental arguments and sources.

### Final Long audit results received from user

- Panel as-of 2026-11-26; 5,491 sessions; 214 tickers; PIT PASS.
- 10-session cohort: 46,243 signals; date-level cohort mean +0.551% at 15 bps, +0.405% at 30 bps, +0.209% at 50 bps. HAC CI for absolute mean: [+0.194%, +0.909%] at 15 bps; [+0.048%, +0.762%] at 30 bps; [-0.148%, +0.566%] at 50 bps.
- 10-session excess mean: +0.080%, -0.067%, -0.262% at 15/30/50 bps. At 15 bps HAC CI [-0.068%, +0.227%], including zero.
- 20-session cohort: 46,243 signals; date-level cohort mean +1.282%, +1.135%, +0.940% at 15/30/50 bps. HAC CI remains positive for absolute mean at all three cost levels.
- 20-session excess mean: +0.238%, +0.092%, -0.104%. At 15 bps HAC CI [-0.028%, +0.505%], including zero; at 30 and 50 bps also includes zero.
- Conclusion: the reconstructed cohort shows positive absolute forward performance, but the evidence does not establish robust excess alpha after plausible costs. At 50 bps excess is negative on both horizons. Treat the result as a weak conditional Long effect, not a proven scalable edge.
- Latest reconstructed Long candidates: 12; overlap with the signal agent's reported 10 = 8/10. Reported names CNRU and HYDR were not reconstructed in the latest list; four names outside the report appeared in the reconstruction. Do not add those extra names to the agent handoff without a new signal decision.
- 60-session pairwise reported-name correlation: mean 0.32, max 0.58 (T/DOMRF). Dependence is material and the window is short.
- Historical candidate diagnostics at 20 sessions:
  - PHOR: mean net +1.54%, median +0.31%, hit 51.0%, mean excess +0.95%; vol60 29.2%; current absolute 20D return -3.5%.
  - RTKM: mean net +0.21%, median +0.28%, hit 51.0%, mean excess +0.70%; vol60 31.9%; current absolute 20D return +0.1%.
  - VKCO: mean net +5.42%, median +3.78%, hit 56.5%, mean excess +3.74%; vol60 96.1%; current absolute 20D return +5.8%.
  - DOMRF: mean net -2.17%, median -0.49%, hit 44.8%, mean excess +7.26%; vol60 15.2%.
  - MTSS: mean net -0.21%, median +0.03%, hit 49.2%, mean excess +0.45%; vol60 24.7%.
  - SMLT: mean net +0.13%, median +0.16%, hit 45.2%, mean excess -0.09%; vol60 82.9%.
  - SVCB: mean net -1.10%, median -2.37%, hit 42.8%, mean excess -0.87%; vol60 29.8%.
  - T: mean net -1.78%, median -0.74%, hit 41.6%, mean excess +0.66%; vol60 22.2%.
  - HYDR: mean net +0.15%, median -0.79%, hit 44.7%, mean excess -0.36%; current vol20/60 unavailable in the audit output.
  - CNRU: only one historical signal; no usable historical performance estimate. Agent handoff reports 64.6% vol20 and 1.06x turnover/median, while the independent snapshot had too little history for vol60. Treat the historical sample as insufficient.
- Important caution: the final output reports exactly 46,243 signals for both 10- and 20-session horizons. This is possible only if no eligible signals lie in the extra tail window that the 20-session horizon excludes, but given the latest candidate reconstruction it is unusual and should be treated as a diagnostic anomaly. The supplied console output does not establish why counts are identical. Do not overstate the HAC inference or use the cohort test as an executable portfolio backtest.
- The by-name mean excess column is gross excess, while mean net includes the 15 bps cost. Compare labels accordingly.

### Iteration 2 — provisional name selection and sizing

Context recovered from prior user instructions:
- Last explicitly stated starting capital: ₽150,000; monthly additions ₽5–10k. Current account value has not been reconfirmed.
- Unified portfolio: Growth/Aggressive 50% (about ₽75,000 at the stated starting capital) / Preservation/Conservative 50%.
- User-stated total tolerable drawdown: 20–25%.
- User prefers portfolio-contribution sizing, with risk assessed using volatility and downside / fat-tail behavior; no fixed per-position risk budget or maximum position cap was supplied.
- Leverage is allowed as a tool in principle, but the user explicitly requires care and statistical justification; no leverage is justified by this weak alpha evidence.
- Conservative remains 100% cash. No transfer between sleeves.

Provisional selection (weights are percentages of the Aggressive sleeve, not of total capital):
- PHOR: 10%.
- RTKM: 7.5%.
- VKCO: 2.5%.
- Aggressive sleeve cash: 80%.
- All other reported Long candidates: 0%.
- All conditional Short candidates: 0%; no borrow, permission, financing, or short implementation evidence.
- Conservative sleeve: 100% cash.

Equivalent percentages of total capital:
- PHOR 5.0%; RTKM 3.75%; VKCO 1.25%; Aggressive cash 40%; Conservative cash 50%.
- Total deployed equity = 10% of total capital; total cash = 90%.
- If ₽150,000 starting capital is still current, indicative amounts are PHOR ₽7,500; RTKM ₽5,625; VKCO ₽1,875; Aggressive cash ₽60,000; Conservative cash ₽75,000. Do not derive share counts without current prices, lot sizes, and execution constraints.

Rationale:
- PHOR receives the largest provisional weight because it combines the best balanced 20-session historical candidate stats among the lower-volatility names in the supplied table. Its current absolute 20D return is negative, so this is not a high-conviction allocation.
- RTKM receives a smaller weight: modestly positive 20-session net and excess results, median positive, but higher volatility and only modest absolute momentum.
- VKCO receives a small satellite weight because it has the strongest historical 20-session results, but ~96% annualized 60-session volatility makes a normal-sized allocation inappropriate.
- CNRU is zero because one historical signal is not a usable sample despite strong current reported RS20 / absolute return.
- HYDR, SVCB, T, SMLT, MTSS and DOMRF are zero because absolute candidate-level history is weak, negative, inconsistent, or (for SMLT) too volatile relative to its weak net/excess evidence.
- All weights are explicitly provisional: no formal risk engine run, no current total NAV confirmation, no exact position/sector caps, no lot-size/execution check, and no left-tail portfolio contribution calculation. The 60-session correlation summary is insufficient for robust covariance estimation.
- No live positions or orders changed; user confirmation remains mandatory.

### Status

- Iteration 1: closed after user returned final audit output.
- Iteration 2: provisional sizing proposal documented; awaiting user review and missing implementation constraints before any actionable order plan.
