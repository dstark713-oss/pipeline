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


## 2026-11-24 | Completed bottom-up allocation review

The 12% equity weight was a tactical reduction on Friday, 2026-11-20, not a strategic base. The former 3/6/9/12% mapping from applying breadth multipliers to that 12% is withdrawn.

LQDT's 30-day price return annualized was reported at 13.57% as of 2026-11-23, net of management fee; 90-day annualized was 14.59%. These are backward-looking floating rates, not guaranteed forward returns. The historical breadth-test cash proxy remains a separate fixed 8% assumption from the user's RGBITR-minus-RGBI calculation.

Candidate review:
- CNRU: 9M revenue +18.9%, adjusted EBITDA +50.7%, net profit +45.3%; but 43.48% realized volatility, P/E around 18x, strong recent rally, and primary-market housing transaction weakness. The 33 RUB proposed dividend is ~3.7% at ~901 RUB; the 14.2% headline used expected annual RUB 86 and average 9M price RUB 605.4. No entry.
- POSI: 9M revenue +48%, shipments +54%, costs -4%, net IFRS loss narrowed to RUB 0.7bn, net debt/EBITDA 0.76x; Q4 is decisive and IFRS earnings remain negative. No entry.
- X5: 9M revenue +11.4%, adjusted EBITDA +12%, but net debt/EBITDA 1.20x, weak FCF versus dividends, rising debt, and proposed dividend yield below LQDT. No entry.
- HYDR: strong momentum and RAS profit growth, but high debt, heavy capex, constrained dividends. No entry.
- FIXR: strong momentum but 9M net profit -24.2%, operating profit -1.4%. No entry.
- LSRG: high momentum but weak available IFRS profitability and leverage/cash-flow risks. No entry.

Existing holdings:
- T: 9M net revenue +26%, operating net profit +35%, ROE 29.1%, raised FY guidance. Retain 10%; no increase while breadth is weak and funding/credit risks remain.
- GCHE: 9M adjusted EBITDA +28.5%, adjusted FCF RUB 19.8bn vs 5.2bn, net debt -7.9%; offset by export sales -10.1%, physical sales -0.3%, interest coverage 3.4x. Retain 2%; no increase.

Final recommendation: T 10%, GCHE 2%, LQDT 88%; no new positions, leverage, or shorts. The 12% equity sleeve is not a base assumption. It is retained after bottom-up review because current holdings remain defensible and no reviewed candidate offers a sufficiently clear risk-adjusted premium over current LQDT.

Confidence: moderate that no reviewed candidate clears the cash hurdle; moderate in retaining T and GCHE; low that exact weights are mathematically optimal. No Qwen review or 2026-11-24 local snapshot supplied. No trades executed or claimed.


## 2026-11-24 | Independent decision after Qwen audit

### Process correction
Qwen's audit is treated as a completed second-opinion input. No further agent-to-agent review loop is required. ChatGPT owns the decision tree, independent verification, follow-up code, and final recommendation; Qwen is not a co-decision-maker.

### Assessment of Qwen findings
- Accept: breadth at 8% (4/50) is a material risk-regime warning; do not add equity risk or buy new names from the primitive screen alone.
- Accept conditionally: low-breadth history reports negative forward equal-weight TOP50 returns on 5/20 sessions. This supports reducing market beta as a risk-control hypothesis.
- Reject as not yet established: the claim that the historical conditional equity return is statistically below LQDT. The supplied report compares historical conditional equity estimates with LQDT returns of 0.037%/0.267%/1.086%, but does not provide a date-matched historical LQDT return series under the same forward-return convention. A current realized LQDT return is not a historical matched benchmark.
- Reject as unsupported sizing: the exact T 10% -> 5% trim is not derived from an estimated T beta, conditional alpha, or portfolio optimization.
- Reject: exiting GCHE solely because it is outside the TOP50 universe. Universe exclusion means the TOP50 breadth model does not directly cover GCHE; it is not a sell signal.
- Qwen's 20-session parameter CI is a confidence interval for an estimated conditional mean, not a prediction interval for an individual future return. The report does not establish the distinction or fully document HAC settings.

### Independent recommendation (not executed)
- T: 10% -> 5% (trim 5 percentage points).
- GCHE: retain 2%.
- LQDT: 88% -> 93%.
- New positions: 0%.

Rationale: T is the only existing equity holding directly represented in the TOP50 breadth universe. A partial reduction halves the covered equity exposure in a weak-breadth regime without pretending the model identifies an optimized target. GCHE remains a small, separately assessed position: recent technical data show it above SMA20 (Z-score +1.26) and issuer fundamentals remain constructive, while no GCHE-specific short-horizon edge has been established. No new name has a validated cross-sectional edge.

This is a risk-control decision under uncertainty, not a claim that 5/2/93 is a statistically optimized portfolio. The expected portfolio-level benefit is modest and depends on the low-breadth signal persisting.

### Follow-up code
Created `scripts/one_use/audit_breadth_transfer_20261124.py` (commit `91e6cca0fd77933f10e17dfaf32c4a2946083b7e`, benchmark alignment fix `baab395d796751d2913ff6d80deb8ec1f260cb73`). It tests multiple HAC lags, non-overlapping samples, expanding-window forecasts, breadth buckets, and optional historical LQDT returns aligned to the same next-session-open to horizon-close convention. It is unexecuted until the user runs it and returns outputs.

### Reversal conditions
- If date-matched LQDT excess is not negative out of sample, do not extend the trim.
- If low-breadth effect survives multiple HAC lags, non-overlapping samples, and walk-forward evaluation, consider further reduction of T.
- If breadth recovers and persists above 20-25%, reassess the beta haircut; this is a provisional review zone, not a validated threshold.
- Reassess GCHE only on its own price/volume/event/fundamental evidence, not by extrapolating TOP50 breadth.

No orders placed. User retains final decision and execution authority.


## 2026-11-24 | Final breadth-transfer audit and allocation decision

### User-run evidence received
The user supplied bucket, HAC-lag sensitivity, matched historical LQDT, non-overlapping timing-offset, and expanding walk-forward outputs. The matched equity/LQDT convention is next-session open to horizon close.

- Low breadth (0-10%), 5 sessions: n=250; equity mean -0.143%, matched LQDT +0.187%, excess -0.330 pp; equity beat LQDT 45.2%.
- Low breadth (0-10%), 20 sessions: n=250; equity mean +1.378%, matched LQDT +0.897%, excess +0.480 pp; equity beat LQDT 48.4%.
- HAC breadth slope at 5 sessions is positive and nominally significant across tested lags 4-39 (t about 2.41-2.68). At 20 sessions it is not significant at any tested lag (t declines from 1.26 to 0.41).
- Breadth buckets are non-monotonic. Low-breadth mean is negative over 5 sessions (-0.115%) but positive over 20 sessions (+1.732%).
- Five-session non-overlap offsets all show negative low-breadth means, with roughly 51-58 observations per offset. Twenty-session offsets are mostly positive but have only 9-19 observations per offset and substantial dispersion.
- Walk-forward model does not beat the unconditional baseline: 5-session MAE 2.0247% vs 2.0211%, RMSE 2.9985% vs 2.9984%, correlation 0.0356; 20-session MAE 4.5612% vs 4.5155%, RMSE 6.2704% vs 6.2187%, correlation -0.1343. Low-breadth actual means are positive on both WF horizons (+0.230% and +2.335%), despite negative/low predictions.
- These results do not establish a tradable breadth strategy. Overlapping forward returns, regime clustering, different complete-case subsets, small low-breadth offset counts, no uncertainty interval for matched excess, and no T-specific beta/alpha remain limitations. The apparent divergence between 20-session buckets, HAC linear fit, and WF predictions needs code/sample-alignment audit rather than narrative smoothing.

### Logic review
1. Breadth 8% (4/50) is a valid descriptive warning about narrow market participation.
2. The 5-session historical matched excess is negative, but modest and not a reliable forecast; WF model fails to add value.
3. The 20-session matched excess is positive on average but beat frequency is below 50%; this is mixed evidence, not a bullish signal.
4. The 20-session HAC relationship is not significant; do not infer a stable linear breadth premium.
5. The WF model is worse than a naive baseline on MAE/RMSE at both horizons; do not use it for prediction or allocation.
6. The market-level TOP50 result does not establish T-specific alpha/beta and does not transfer to GCHE, which is outside the universe.
7. No new candidate has a validated edge over matched LQDT.

### Final recommendation (not executed)
Maintain the latest user-reported actual allocation:
- T 10%: HOLD. Do not apply the previously suggested 10% -> 5% trim; that sizing was not supported by T-specific beta/alpha or a portfolio optimization and is withdrawn.
- GCHE 2%: HOLD. Evaluate independently; TOP50 breadth does not cover it.
- LQDT 88%: HOLD.
- New positions: none.

This is a deliberate no-change decision, not a claim that 10/2/88 is optimal. Breadth is a reason not to add equity beta and to watch short-horizon risks, but not enough to force a trim. The earlier 5/2/93 recommendation was not executed and is superseded. No orders placed.

### Next research gates
- Audit code and exact sample alignment among bucket/HAC/matched-LQDT/WF outputs, especially the 20-session low-breadth divergence.
- Add block-bootstrap or regime-aware uncertainty intervals for matched excess; account for regime clustering and overlapping horizons.
- Test a pre-specified breadth rule walk-forward, with realistic friction.
- Estimate T-specific beta/conditional alpha and incremental portfolio risk before proposing any breadth-driven T sizing.
- Keep GCHE on its own issuer/price/event evidence.


## 2026-11-24 | GCHE individual review completed after process correction

### Process failure acknowledged
The previous decision tree correctly said that GCHE's exclusion from TOP50 requires separate issuer-specific assessment, but the final recommendation labelled GCHE HOLD without actually performing that review. This was a process failure. Model-universe exclusion is not evidence for HOLD or EXIT. A position cannot be marked fully reviewed until its own issuer, price, liquidity, events, and horizon analysis is completed.

### GCHE evidence reviewed
- Issuer 9M 2026 disclosure (17 Nov): revenue +6.4%; adjusted gross profit +26.1%; adjusted EBITDA +28.5% to RUB 51.2bn; reported net profit +20.3%; adjusted net profit +135.9% to RUB 24.2bn; adjusted FCF RUB 19.8bn vs RUB 5.2bn; net debt RUB 131.1bn, down 7.9%; ND/adjusted EBITDA 1.9x; interest coverage 3.4x.
- Operating offsets: total physical sales -0.3%; export volumes -10.1%, average export realization -5.5%; Foodservice -0.9%; retail/wholesale +1.1%. Margin benefited from pricing/mix, procurement efficiency and favorable grain conditions. Capex reduced 8.2%, supporting FCF but potentially limiting future capacity investment if sustained.
- 24 Nov public price snapshot around RUB 3,729, down about 1.61% after 23 Nov rise around 3.67%; intraday range about RUB 3,683-3,775. Volatile/choppy near-term tape. External quote/technical sources may differ by timestamp and adjusted/unadjusted basis; do not synthesize conflicting indicators.
- 1 session: neutral / elevated short-term range and event risk.
- 5 sessions: neutral; fundamental release is constructive but price action is choppy.
- 20 sessions: moderately positive fundamental bias; export and feed-cost/margin risks remain.
- A reported poultry mortality incident could not be confirmed from reliable sources and is excluded from base case.

### GCHE decision
HOLD existing 2%; do not add. This is now supported by a completed, though not exhaustive, issuer-specific review: improving adjusted profitability, FCF and leverage support retaining a small position; export/foodservice weakness, feed-cost sensitivity, interest burden and volatile price action argue against adding. No validated alpha model or reliable expected-return premium over LQDT has been established. No cost basis or exact position risk budget supplied; no claim about unrealized P&L or mathematically optimal sizing. Reassess if export restrictions worsen, feed costs reverse, margin/FCF deteriorate, debt/interest coverage worsens, or a confirmed technical breakdown occurs.

The portfolio recommendation remains T 10%, GCHE 2%, LQDT 88%, no new positions, but the GCHE HOLD is now based on its own evidence rather than TOP50 exclusion. No orders placed.


## 2026-11-25 | Final paired-excess robustness audit and allocation decision

### User-run output
Snapshot: 2026-11-25; 5,490 calendar sessions; LQDT 1,074 ISS candles, 994 aligned daily returns. Metric: asset forward return t+1..t+h minus matched LQDT return over the same dates, conditional on breadth at t. HAC Newey-West Bartlett lag 20; moving-block bootstrap length 20, 1,000 reps; episode bootstrap resamples horizon-aware low-breadth clusters.

The script merges low-breadth dates separated by fewer than h sessions. Total episodes: 111 (H1), 63 (H5), 47 (H20). Valid episodes are much fewer:
- T: 14 / 7 / 4 at H1/H5/H20.
- GCHE: 26 / 17 / 10 asset-specific; 14 / 7 / 4 common dates.
- EW-TOP50: same complete-case counts as GCHE.

At breadth <=10%:
- T excess: H1 +0.161%, H5 +0.610%, H20 +0.504%; every available HAC and calendar-block interval includes zero. Episode bootstrap is NA at H5/H20 because only 7/4 valid clusters. H20 median is -1.379%.
- GCHE excess: H1 -0.188% asset-specific / -0.313% common; H5 -0.156% / -1.245%; H20 -0.918% / -4.103%. Asset-specific intervals include zero at every horizon. H20 common HAC interval is [-7.204%, -1.002%], but calendar-block interval is [-6.513%, +0.076%] and only four valid clusters remain; episode bootstrap NA.
- EW-TOP50 excess: H1 -0.117% asset-specific / -0.139% common; H5 +0.022% / -0.298%; H20 +0.210% / -1.800%. All available intervals include zero.

### Interpretation
The large nominal date count is not an independent sample count. H20 common-date results are supported by only four horizon-aware clusters. The negative GCHE H20 common-date mean is a warning, not robust exit evidence. Positive T means are not evidence of a reliable premium. The low-breadth experiment does not validate a market-timing rule or an allocation multiplier.

The <=5% and <=15% rows were generated in the output CSV but were not included in the console excerpt supplied for this final review. Threshold robustness is therefore not verified in this entry. The episode definition is horizon-aware but not uniquely correct; episode bootstrap remains descriptive and assumes these clusters are appropriate resampling units.

### Issuer refresh
T: 24 Nov company operating release for October showed loan portfolio +25% YoY to RUB 4.2tn, business loans +62%, client funds plus brokerage assets +5% to RUB 6.5tn, but customer funds on accounts alone RUB 3.9tn were down 9% YoY and 3.6% MoM. October bank profit RUB 160.5bn is RAS bank profit, not consolidated IFRS. Funding mix is a monitoring risk; not proof of funding stress. 9M operating profit growth remains counterevidence. Price feeds on 25 Nov conflicted; exact technical state is provisional.
GCHE: 9M results remain strong on adjusted profitability/FCF and lower leverage, but volumes were flat-to-down, exports -10.1%, foodservice -0.9%, transport expenses +10.4%, and capex was reduced. External quote feeds on 25 Nov conflicted; exact technical state is provisional.

LQDT trailing annualized returns from a 25 Nov market comparison: 30d 14.56%, 90d 14.65%. These are backward-looking and floating, not a guaranteed forward return. Historical comparisons use the actual date-matched LQDT ISS series, not the current trailing yield.

### Final recommendation (not executed)
HOLD / NO CHANGE at latest known user-reported weights:
- T 10%: HOLD, no add, no breadth-driven trim.
- GCHE 2%: HOLD, no add, no breadth-driven exit.
- LQDT 88%: retain.
- New equities: 0%.
- No leverage or shorts; no orders placed.

This is not a claim that 10/2/88 is optimal. The supplied evidence does not establish a robust excess-return penalty or premium, does not estimate T-specific alpha or GCHE-specific beta, and does not determine optimal position weights. A 5% T target or GCHE exit would be false precision on this dataset. Not adding is justified because no candidate has a verified after-cost premium over LQDT.

### Mandatory self-audit
- Latest known portfolio snapshot is 23 Nov, not reconfirmed after that date.
- Breadth reference 8% (4/50) comes from prior user local snapshot.
- LQDT data are separate ISS candles, 1,074 raw rows / 994 aligned daily returns.
- H20 episode counts too small for stable cluster inference; some episode bootstrap outputs NA.
- <=5% and <=15% threshold results not reviewed in supplied excerpt.
- Quote feeds for T and GCHE on 25 Nov conflict; no fully aligned local price/volume snapshot supplied.
- Current intrinsic valuations and forward expected return distributions for T/GCHE not established.
- Portfolio covariance/marginal risk optimization not performed.
- Full new-candidate universe not refreshed in this final cycle.
- Qwen review not supplied.
- No trade execution claimed.

Confidence: high that this breadth test does not justify automatic allocation action; moderate that no new equity should be added; low-to-moderate that exact current weights are optimal. Preserve this decision as-of 25 Nov and do not rewrite it with hindsight.
