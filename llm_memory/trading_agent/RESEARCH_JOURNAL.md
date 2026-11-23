# Trading Agent Research Journal

Chronological log of role setup, daily allocation investigations, decisions, tool audits, and lessons. This journal belongs to the Trading Agent and is separate from the user's daily report and the Research Agent's journal.

## 2026-11-23 | Agent initialization and repository reconnaissance

### Initial setup
The user defined a daily workflow triggered by "Аллокация на сегодня". The initial setup documented portfolio review, local market tools, news, fundamentals, semantic analysis, Qwen-only review, allocation synthesis, and a future API direction.

### Repository reconnaissance
Inspected the repository root, `llm_memory/`, existing specialist-agent memories, the deterministic screener specification, the dataset refresh implementation, and relevant script inventories.

Existing deterministic stack:
- `scripts/dataset/fresh/refresh_pipeline.py`
- `scripts/experiments/primitives/05_build_primitive_features.py`
- `scripts/tools/01_primitive_screener.py`
- `docs/tools/01_primitive_screener.md`

The screener exposes instrument state (`drawdown_60`, `zscore_sma20_20`, `realized_vol_60`) and separate market context (`breadth_change_5`, `breadth_sma20`). It is descriptive/read-only and does not generate buy/sell signals or portfolio weights. Local runtime status is not established by repository inspection.

## 2026-11-23 | Role correction: learn allocation through real-market cycles

### User correction
The user clarified that the Trading Agent's immediate and only responsibility is supervised allocation reasoning on the real market. The user also clarified the practical research handoff: when information is missing from existing tools, the agent should create a focused one-use script, the user runs it locally, and returns the result. The script may be provided in chat or committed to GitHub for the user to pull. Future Codex/Python access should enable direct analysis of accessible project data.

### Initial allocation snapshot
User-reported on 2026-11-23:
- T: 10%
- GCHE: 2%
- LQDT: 88% (clarified later in the same allocation workflow; this is a money-market fund, not idle cash).

### Agreed operating split
- Portfolio Reader: maintain a simple allocation ledger from the user's updates; no complex reader.
- Daily Market Snapshot: request local market/screener outputs from the user.
- News & Fundamentals: agent gathers current public information from the internet.
- Semantic Engine: agent performs direct LLM reasoning over sourced facts and events.
- Qwen Reviewer: user runs Qwen and supplies its response; Qwen is the only second-opinion LLM.
- Allocation Engine: agent's own reasoning and recommendation; maintain this journal.
- Research gaps: agent specifies the missing information and creates a complete, read-only one-use script where practical; user executes and returns outputs.
- API orchestration: deferred until repeated manual allocation cycles reveal a concrete need.

## 2026-11-24 | Allocation decision and constraints recorded

### User-supplied portfolio and modeling constraints
- Current known portfolio: T 10%, GCHE 2%, LQDT 88%; total 100%.
- At most 10 equity names simultaneously.
- Aggregate signed portfolio loading range: -0.5 to +1.5.
- No per-security weight limit supplied.
- No separate gross-exposure limit supplied.
- No sensitivity checks for the current breadth experiment.

The aggregate loading range is not a per-name limit. Do not invent an individual-position cap or gross-exposure cap. Negative weights and leverage are allowed by the model's stated range, but are not recommended by default.

### Breadth rule clarification
The 3%, 6%, 9%, and 12% historical equity exposure scenarios are derived from the current 12% equity baseline multiplied by the documented breadth multipliers 25%, 50%, 75%, and 100%. They are not independently optimized values or position limits.

The historical cash proxy is fixed at 8% annual effective across the full test, based on the user's calculation from RGBITR minus RGBI. It is not actual LQDT historical performance. The user's current LQDT yield estimate is approximately 12% annualized and must remain a separate, floating/current assumption. Sensitivity checks are excluded from the current run.

### Latest local market snapshot supplied
For 2026-11-23:
- breadth above SMA20: 12% (6/50);
- 5-session breadth change: -42 percentage points;
- all 50 instruments had valid data;
- IMOEX +1.30% (figure from the user's prior snapshot).

Interpretation: the index rebound was narrow and breadth remained weak. The documented rule maps this to the 25% multiplier, or 3% of the 12% baseline equity sleeve. Because the rule is not yet validated, this is a diagnostic warning, not an automatic instruction to cut live positions to 3%.

### Issuer research checked for this decision
**T / T-Technologies**
- Official 3Q/9M 2026 IFRS release dated 2026-11-10: 9M net revenue +26% to RUB 648.3bn; operating net profit +35% to RUB 162.2bn; 3Q operating net profit +41% to RUB 63.6bn; 9M ROE 29.1%, 3Q ROE 32.3%.
- Management raised 2026 guidance to operating net profit and aggregate dividends per share growth above 25%, with ROE around 30%; board recommended RUB 4.8 quarterly dividend.
- Credit risk cost 5.0% for 9M versus 6.0% a year earlier; NPL 7.0% at 2026-09-30.
- Funding-mix concern: an external review of the 9M report noted loan portfolio growth alongside lower customer funds and loan-to-customer-funds rising to 98.4%. Treat as a monitoring risk, not proof of a liquidity crisis.
- Corporate transactions (Tochka, Auto.ru, CIAN proposal) create execution and capital allocation complexity; track actual dilution and EPS accretion.
- Primary source: https://t-technologies.ru/press-releases/
- Supporting analysis: https://bf.arsagera.ru/tcs_group_holding_plc_tcsg/itogi-9-mes-2026-g-udesevlenie-fondirovaniia-podderzivaet-rost-pribyli

**GCHE / Cherkizovo**
- Official 9M 2026 disclosure dated 2026-11-17: revenue +6.4% to RUB 224.2bn; adjusted gross profit +26.1%; adjusted EBITDA +28.5%; adjusted net profit RUB 24.2bn versus RUB 10.3bn; adjusted FCF RUB 19.8bn versus RUB 5.2bn.
- Net debt down 7.9% to RUB 131.1bn; net debt/adjusted EBITDA 1.9x; interest coverage 3.4x.
- Offsetting risks: physical sales -0.3%; exports -10.1%; food-service -0.9%; management cited China poultry restrictions, imported chicken competition, weak restaurant demand, pork oversupply, and subdued crop-segment economics. Capex down 8.2%, supporting FCF but potentially constraining capacity growth if sustained.
- Primary disclosure: https://www.e-disclosure.ru/portal/event.aspx?EventId=JWyX1VWphUOrx7O5ugOm6g-B-B

### Final recommendation
**HOLD / NO CHANGE** on the latest supplied evidence:
- T 10%
- GCHE 2%
- LQDT 88%
- no new positions; no leverage or short exposure recommended.

Rationale:
- T's reported fundamentals support retaining the existing position, but valuation and funding-mix uncertainty do not establish a reason to add.
- GCHE's improved adjusted profitability and FCF support retaining a small position, while exports, demand, interest burden, and capex risks argue against increasing it.
- Breadth at 12% and falling sharply argues against adding equity risk after a narrow index rebound.
- Candidate technical rankings (including HYDR, POSI, CNRU, FIXR, LSRG) are not sufficient for purchases without fundamental and valuation review.
- LQDT's current yield is a meaningful alternative, although it floats and is not guaranteed.

### Evidence boundaries
- This recommendation uses the latest user-provided local market snapshot dated 2026-11-23. No 2026-11-24 local market snapshot was supplied.
- Corrected breadth backtest has not yet been created or run. No result is claimed.
- Qwen review was not supplied for this cycle.
- No orders were placed and no execution is claimed.
- Confidence: moderate in no-change as the least-assumptive action; low in the claim that the exact 10%/2% stock weights are optimal.


## 2026-11-24 | Correction: tactical 12% reduction is not a strategic baseline

The user corrected a material reasoning error: the 12% equity allocation was a tactical reduction of positions on Friday, 2026-11-20. It was not a strategic baseline, target exposure, or validated risk budget.

The prior mapping of breadth multipliers 25/50/75/100% to portfolio equity exposures 3/6/9/12% by multiplying them by 12% was therefore invalid. The decision-tree document was amended to withdraw that mapping. Do not use those exposures in allocation reasoning or historical testing as if they were justified by the strategy.

The user also clarified that the allocation decision was not final and asked the agent to return to substantive security/portfolio research rather than continue discussing theoretical exposure-limit definitions. The earlier HOLD / NO CHANGE should be treated as provisional and incomplete, not as the final decision.

Next work: complete issuer/fundamental/valuation review of the current holdings and strongest candidates from the local technical screen, compare them against LQDT, then formulate a defensible target allocation. Do not anchor target equity exposure to the Friday 12% tactical state. Do not ask the user to repeat already supplied portfolio constraints.
