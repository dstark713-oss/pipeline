# Allocation Decision Tree

Last updated: 2026-11-24
Decision state: INCOMPLETE / PROVISIONAL (the earlier HOLD / NO CHANGE is withdrawn as a final decision)
Evidence cutoff: latest user-provided local market snapshot dated 2026-11-23; issuer information checked through 2026-11-24.

This document records the current decision logic and the allocation decision. It is a working policy, not a claim that the rules have been statistically validated.

## 1. Current portfolio state

User-reported portfolio snapshot, 2026-11-23:
- T: 10%
- GCHE: 2%
- LQDT: 88%

Current equity allocation: 12%. This is the result of a tactical position reduction made on Friday, 2026-11-20, as reported by the user. It is not a strategic baseline, target exposure, or validated risk budget. LQDT is a money-market fund, not idle cash. The user estimates its current effective yield at approximately 12% annualized (key rate less fund expenses); this is a user estimate for the current environment, not a guaranteed return and not a historical series.

Historical cash benchmark for the breadth experiment:
- 8% annual effective rate across the full test period.
- User-provided estimate derived from the difference between RGBITR and RGBI.
- This is not actual LQDT performance. Do not relabel it as LQDT history.
- No sensitivity analysis is authorized for the current run.

## 2. Portfolio construction constraints supplied by the user

- Maximum 10 simultaneously held equity names.
- Total portfolio loading range: -0.5 to +1.5.
- Interpret loading as the signed aggregate of position weights unless the user later defines it differently.
- No per-security weight limit has been supplied.
- No separate gross-exposure limit has been supplied. Do not invent one.
- Negative weights are permitted (short exposure); loading above +1.0 permits leverage.
- These are portfolio-model constraints, not a mandate to use shorts or leverage.

Do not confuse:
- historical breadth-test equity sleeve scenarios (3%, 6%, 9%, 12%);
- portfolio-level signed loading constraint (-0.5 to +1.5);
- a per-security weight constraint (none supplied).

## 3. Breadth rule and origin of 3/6/9/12%

The documented breadth heuristic uses a 12% baseline equity sleeve and a multiplier:
- breadth >= 0.50 and breadth_change_5 > 0: multiplier 1.00;
- breadth >= 0.50 and breadth_change_5 <= 0: multiplier 0.75;
- breadth < 0.50 and breadth_change_5 > 0: multiplier 0.50;
- breadth < 0.50 and breadth_change_5 <= 0: multiplier 0.25.

Therefore the historical exposure scenarios are:
- 12% x 0.25 = 3%;
- 12% x 0.50 = 6%;
- 12% x 0.75 = 9%;
- 12% x 1.00 = 12%.

These are not optimized weights, forecasts, or independent portfolio constraints. They are simply the four exposure levels implied by applying the documented multiplier to the current 12% equity baseline. The 50% breadth threshold is fixed for this test; no threshold grid or sensitivity sweep is to be run.

## 4. Decision sequence

### Step A — Verify the decision frame
1. Record decision date, market-data cutoff, and latest user-provided portfolio snapshot.
2. Reconcile all known holdings and weights. Never infer an unreported position or cash balance.
3. Mark local screener data stale if it does not include the latest completed session.
4. Distinguish the live LQDT yield estimate from the fixed 8% historical cash benchmark.

### Step B — Assess broad market regime
1. Read breadth level and its 5-session change.
2. Treat index return and breadth as separate evidence. A rising index with weak breadth is a narrow rebound, not broad risk-on.
3. Apply the documented multiplier only as an exposure-control hypothesis. Do not treat it as validated until the corrected historical test has been run and audited.
4. Do not increase exposure solely because of one positive index session.

### Step C — Assess each held security
For each holding:
1. Check latest official financial results and material disclosures.
2. Map results into earnings, cash flow, balance sheet, credit/operating risk, valuation, and expectations.
3. Compare technical state with the fundamental thesis; neither alone is sufficient.
4. Record the strongest counterargument and explicit thesis-break conditions.
5. Separate confirmed issuer facts from analyst interpretations and unverified hypotheses.

### Step D — Compare equity risk with the alternative
1. Compare expected equity return with the current LQDT alternative, net of fees/taxes/transaction costs where known.
2. Use the 8% historical benchmark only in the historical breadth experiment.
3. Do not assume that a strong company is attractive at any price.
4. If the expected edge is unclear, no-change or cash is a valid decision.

### Step E — Portfolio synthesis
1. Respect the maximum of 10 simultaneous equity names.
2. Keep aggregate signed loading within [-0.5, +1.5].
3. Do not add an individual-position or gross-exposure limit unless the user supplies one.
4. Check concentration, correlation, liquidity, turnover, and implementation costs using available evidence.
5. A new position requires a positive thesis and a reason to prefer it over the existing holdings and LQDT.
6. A reduction requires a broken/weakened thesis, excessive risk, or a better use of capital; do not sell solely because a technical indicator looks stretched.

### Step F — Record the decision
State:
- target weights and change from baseline;
- facts supporting the decision;
- strongest opposing case;
- invalidation conditions;
- confidence and missing evidence;
- whether the decision was recommended or actually executed (execution is user-reported only).

## 5. Provisional assessment for 2026-11-24 (not a final allocation)

### Provisional snapshot only
The last known weights were:
- T: 10%
- GCHE: 2%
- LQDT: 88%
- Equity sleeve: 12%

This is not a final recommendation. Candidate research and valuation comparison remain incomplete.

This decision uses the latest local market snapshot supplied by the user on 2026-11-23. No local snapshot for the 2026-11-24 session was supplied in this decision cycle, so the decision must not be described as based on 2026-11-24 breadth or closing prices.

### Market evidence
User-run local output for 2026-11-23:
- breadth above SMA20: 0.12 (6 of 50);
- 5-session breadth change: -0.42;
- all 50 instruments had valid data;
- IMOEX rose 1.30% that session (secondary-source figure from the user's prior snapshot).

Interpretation: index rebound was not broad-based. The breadth state maps to the 25% multiplier under the unvalidated heuristic. Because the reference exposure has not been independently established, this does not translate into a defensible target portfolio weight. It is a negative market-regime input, not a mechanical instruction to cut positions.

### T — retain 10%, do not add
Positive evidence:
- Official 3Q/9M 2026 results: 9M net revenue +26% YoY to RUB 648.3bn; operating net profit +35% to RUB 162.2bn; 3Q operating net profit +41% to RUB 63.6bn; 9M ROE 29.1%, 3Q ROE 32.3%.
- Management raised 2026 guidance to operating net profit and aggregate dividends per share growth above 25%, with ROE around 30%.
- Board recommended a quarterly dividend of RUB 4.8 per share.
- The company reported credit-risk cost of 5.0% for 9M versus 6.0% a year earlier; NPL ratio was 7.0% at 30 September.
- Official report: https://t-technologies.ru/press-releases/ (10 November 2026, 3Q 2026 IFRS release).

Counterevidence / risks:
- The loan portfolio grew while customer funds declined during the first nine months; an external analysis of the 9M report highlighted loan-to-customer-funds rising to 98.4%. Funding structure and liquidity therefore deserve monitoring.
- Cost of risk remains material even though it improved year over year; deterioration in credit quality could reverse earnings momentum.
- The acquisition/integration agenda (Tochka, Auto.ru, CIAN proposal) adds execution and capital-allocation complexity. The Tochka transaction includes share issuance; monitor final dilution and EPS accretion rather than assuming management's forecast will be achieved.
- No current valuation analysis in this decision packet establishes that adding at today's price has positive expected excess return versus LQDT.

Conclusion: fundamentals support retaining the existing position; they do not by themselves justify increasing it from 10%.

### GCHE — retain 2%, do not add
Positive evidence:
- Official 9M 2026 disclosure dated 17 November: revenue +6.4% to RUB 224.2bn; adjusted gross profit +26.1%; adjusted EBITDA +28.5%; adjusted net profit RUB 24.2bn versus RUB 10.3bn; adjusted FCF RUB 19.8bn versus RUB 5.2bn.
- Net debt declined 7.9% to RUB 131.1bn; net debt/adjusted EBITDA 1.9x.
- Primary disclosure: https://www.e-disclosure.ru/portal/event.aspx?EventId=JWyX1VWphUOrx7O5ugOm6g-B-B

Counterevidence / risks:
- Physical sales declined 0.3%; export sales declined 10.1%, and food-service sales declined 0.9%.
- Management cited restrictions on poultry shipments to China, competition from imported Chinese chicken fillet, weak food-service demand, oversupply in pork, and weaker crop-segment economics.
- Interest coverage was 3.4x, materially below the 2020-2022 range cited by the company.
- Capex declined 8.2%; this supported FCF but may constrain capacity growth if sustained.
- Local technical output showed price +4.71% above SMA20 and z-score +2.61 under the project's nonstandard standardized-distance formula. This is not a probability, classical statistical test, or stand-alone sell signal.

Conclusion: improved profitability and FCF support keeping a small position. Export, demand, leverage-cost, and capex risks do not support increasing it.

### Why no new position
The local candidate comparison showed several strong momentum names (including HYDR, POSI, CNRU, FIXR, LSRG), but no complete fundamental and valuation review for them has been completed. Technical ranking alone is insufficient to displace LQDT or justify adding a new name. The maximum of 10 names is a ceiling, not a target.

### Why not cut existing positions immediately
- No verified thesis break was identified for T or GCHE in the reviewed disclosures.
- The breadth rule is an unvalidated exposure hypothesis, not a proven forced de-risking rule.
- Cutting to the rule-implied 3% equity sleeve would turn an unvalidated backtest hypothesis into a live trading mandate.

## 6. Work required before final allocation

1. Complete fundamental and valuation review of the strongest candidates from the local technical comparison, prioritizing HYDR, POSI, X5, and selectively CNRU/FIXR/LSRG where liquidity and business risks justify further work.
2. Reassess T and GCHE against those candidates and the current LQDT alternative; do not preserve their current weights merely because they are the known holdings.
3. Form target weights from expected return, downside, liquidity, correlation, and portfolio constraints, not from the tactical 12% Friday reduction.
4. State explicitly if a security cannot be valued responsibly with available data. Do not invent target weights to fill the allocation.

## 7. Invalidation and review triggers

Reassess the hold decision if any of the following occurs:
- New local snapshot shows a materially different breadth regime, especially persistent deterioration or broad recovery; do not act on one day alone.
- T reports material deterioration in cost of risk, NPLs, funding mix, capital adequacy, or guidance; or dilution/integration terms change materially.
- GCHE reports sustained weakness in poultry pricing/volumes, export restrictions worsen, adjusted FCF reverses, net debt rises, or interest coverage deteriorates.
- The expected net return on equities no longer compensates for LQDT's current yield and portfolio risk.
- The corrected breadth experiment, once actually run, contradicts the heuristic or reveals material timing/coverage bias.

## 8. Pending work and status

- Corrected breadth backtest: not yet created/run in this decision record. No sensitivity checks. The earlier 3/6/9/12% mapping is withdrawn.
- Historical cash proxy: fixed 8% annual effective, user-provided from RGBITR minus RGBI.
- Current LQDT yield: user estimate around 12% annualized; floating/current only.
- Qwen review: not supplied for this cycle.
- Local 2026-11-24 market snapshot: not supplied.
- No orders placed or execution claimed.

## 9. Confidence

- Confidence in the earlier HOLD / NO CHANGE as a provisional least-assumptive action: low-to-moderate; it is not a completed allocation decision.
- Confidence that 10% T and 2% GCHE are optimal weights: not established. The tactical origin of the 12% stock allocation does not justify retaining it as a strategic target.
- Confidence in the breadth multiplier as a live allocation rule: low until the corrected historical test is completed.
