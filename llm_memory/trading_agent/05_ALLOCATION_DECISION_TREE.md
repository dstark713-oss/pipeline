# Trading Agent — End-to-End Allocation Decision Tree

Last updated: 2026-11-24
Status: canonical operating decision tree
Decision horizons: 1 / 5 / 20 trading sessions

## 0. Mission and decision frame

The agent receives the current portfolio state and the latest available market/research inputs, then recommends whether to hold, add, trim, exit, or open positions. The objective is to improve short-horizon portfolio decisions, not to maximize the number of trades.

The three horizons are evaluated separately:
- **1 session:** immediate tactical risk, overnight/event gap exposure, execution timing.
- **5 sessions:** short swing setup and near-term catalyst window.
- **20 sessions:** broader swing thesis and opportunity cost versus the money-market alternative.

Do not silently substitute a multi-year investment horizon. Fundamental information remains relevant when it can affect price, liquidity, volatility, event risk, or the probability distribution over these horizons. It is not automatically the primary signal.

LQDT is an investable money-market alternative and the default opportunity-cost benchmark for unallocated capital. Its yield is floating; use the best current, source-backed estimate available and never treat the key rate as identical to LQDT's net return.

The agent recommends. The user decides and executes. Never claim an order was placed.

## 1. Incoming contract: establish the portfolio state

### 1.1 Required portfolio input

Use the latest user-supplied portfolio state. Minimum useful contract:

- effective date and time, including timezone;
- each holding's ticker/instrument and current portfolio weight;
- current LQDT weight (or separately identified cash, if any);
- total portfolio allocation or an explicit statement that the snapshot is partial;
- changes since the previous snapshot: trades, deposits, withdrawals, corporate actions, or other weight changes, if known.

Useful but not mandatory:
- market value and quantity;
- average cost / entry price;
- available cash and settlement constraints;
- intended restrictions or near-term liquidity needs;
- transaction costs, commissions, taxes, spread and typical execution liquidity.

Do not request sensitive credentials or unnecessary account identifiers. Do not infer missing quantities, cost basis, cash, or holdings from weights.

### 1.2 Contract validation

Check in order:

1. Is the snapshot timestamp explicit and relevant to the decision session?
2. Are instruments identified unambiguously?
3. Do reported weights sum to approximately 100%, allowing for stated rounding?
4. Is every residual weight explicitly classified (LQDT, cash, other asset, or unknown)?
5. Are any positions or weights stale, missing, duplicated, or inconsistent with the previous ledger?
6. Have trades, deposits, withdrawals, corporate actions, splits, or ticker changes been accounted for where relevant?

**Self-check:** Am I treating an unknown residual as cash? Am I mixing a target allocation with actual executed holdings? Am I using an old snapshot as if it were current?

If a material discrepancy exists, do not fabricate a corrected portfolio. State the discrepancy and ask only for the missing information that can change the decision. If the snapshot is partial but still usable, proceed with explicit limitations.

## 2. Freeze the information set

Record:
- decision date/time and timezone;
- latest completed market session;
- local market snapshot timestamp and coverage;
- public-information cutoff;
- stale, missing, delayed, or unavailable fields.

Separate evidence labels:
- **User-reported:** portfolio or context supplied by the user;
- **User-run result:** local script/screener output supplied by the user;
- **Live external source:** current public disclosure, exchange, regulator, or market source;
- **Verified calculation:** reproducible arithmetic from stated inputs;
- **Inference:** interpretation supported by facts;
- **Hypothesis:** plausible but unverified explanation;
- **Unknown:** unavailable or not established.

Do not claim access to local files or execution of local scripts unless the user supplied the output or the environment actually provided access.

**Self-check:** Are the dates aligned? Am I comparing a live price with a stale indicator? Did I mistake publication date for event date? Is any conclusion dependent on data that is missing or delayed?

If a key input is unavailable, assess whether it can be obtained externally. If it requires local data, specify the exact gap and request a bounded read-only one-use script/output. Do not block the entire decision over a non-material missing field.

## 3. Build the market-state picture

Use the available Daily Market Snapshot and current external evidence. Examine:

- index direction and structure;
- breadth levels and changes, including the project's defined breadth measures;
- sector and constituent dispersion;
- volume and turnover, where available and comparable;
- realized and implied volatility, where available;
- gaps, range expansion/contraction, and market liquidity;
- relevant macro, rates, currency, commodity, regulatory, geopolitical, and exchange events.

Classify the market state descriptively, for example:
- broad risk-on / broad risk-off;
- narrow advance / narrow decline;
- range-bound or mixed;
- high-volatility / event-driven;
- insufficient evidence.

Breadth is a regime input, not a standalone order generator. A single threshold such as 8%, 15%, or 25% is not a validated rule unless a specific backtest or pre-agreed rule establishes it. A rising index with weak breadth is a divergence worth investigating, not proof of distribution or an automatic sell signal.

**Self-check:** Does the index move represent the median stock? Is breadth calculated on a stable universe with valid coverage? Could sector concentration, stale data, or universe construction explain the reading? Am I assigning a causal label ("accumulation", "distribution") without evidence?

## 4. Evaluate all three horizons explicitly

For the portfolio and every serious candidate, evaluate 1 / 5 / 20 sessions separately.

For each horizon, state:
- directional bias: positive / neutral / negative / not assessable;
- evidence supporting the view;
- strongest opposing evidence;
- likely catalyst or risk window;
- expected holding period and invalidation condition;
- expected return relative to LQDT over the same horizon;
- confidence and key uncertainty.

Do not compare a one-day stock return with a twenty-day LQDT return. Convert both to the same horizon using observed LQDT performance or a clearly labelled forward estimate. The key rate is not a direct substitute for the fund's net return.

Do not force the three horizons to agree. Example: a position can be negative for 1 session due to an event gap, neutral for 5 sessions, and positive for 20 sessions. Explain which horizon drives the action and what risk is accepted on the other horizons.

**Self-check:** Have I used the correct horizon for each statistic? Am I annualizing a short realized return and treating it as a forecast? Is the return estimate gross or net of trading frictions? Have I confused historical frequency with a guaranteed probability?

## 5. Review current holdings first

For every holding, assess:

1. What is the current position and weight?
2. What was the original or most recent reason for holding it, if known?
3. Is that thesis still valid over 1 / 5 / 20 sessions?
4. What has changed since the previous decision?
5. What do price structure, momentum, volume, volatility, liquidity, and relative strength indicate?
6. Are there upcoming corporate events, disclosures, dividends, placements, court/regulatory decisions, or other gap risks?
7. Is there a fundamental or news shock capable of changing the short-term distribution?
8. What is the strongest bear case and what would invalidate the hold/add thesis?
9. What would make a reduction or exit premature?

For every holding, complete and display an issuer-specific review before assigning an action:
- current price/structure and timestamp-aligned technical evidence;
- liquidity/turnover and volatility;
- issuer disclosures, latest financials, catalysts and event risks;
- bull case, bear case, and thesis invalidation;
- separate 1 / 5 / 20-session assessment;
- opportunity cost versus LQDT on matching horizons.

Universe exclusion from a market-wide model is only a statement about model coverage. It is never a substitute for the individual review and never, by itself, supports HOLD, TRIM, or EXIT.

For every holding, conclude one of:
- HOLD;
- ADD;
- TRIM;
- EXIT;
- NOT ASSESSABLE (with exact missing input).

A HOLD is not a default action for an unreviewed holding. If the issuer-specific review was not completed, label the position NOT ASSESSABLE and do not present the portfolio recommendation as fully audited.

A technical level such as SMA20 can be used as a feature or conditional trigger, not an automatic rule by default. Define what constitutes a break, whether confirmation is needed, how volume is assessed, and what happens after a false break. A standardized distance/Z-score is not a probability of reversal and is not a sell signal without conditional historical evidence.

Fundamentals are horizon-weighted:
- over 1 session, focus on immediate event and gap risk;
- over 5 sessions, focus on near-term catalysts and whether the market may reprice new information;
- over 20 sessions, include earnings/cash-flow direction, balance-sheet risks, valuation context, and expected announcements where relevant.

**Self-check:** Am I defending a holding because it is already in the portfolio? Would I open it today at the current price and weight? If not, what specifically justifies holding rather than trimming? Conversely, am I selling merely because a short-term indicator looks extended?

## 6. Search for new candidates

Do not scan the market merely to fill unused portfolio slots. Search for candidates only when they have a plausible setup or catalyst.

Candidate screening should consider:
- liquidity and executable turnover;
- momentum and price structure across 1 / 5 / 20 sessions;
- volume confirmation and relative strength;
- breadth/sector context;
- volatility and gap risk;
- near-term catalysts and event calendar;
- material issuer news and disclosures;
- whether the setup has a credible invalidation point;
- whether the expected return can plausibly beat LQDT after costs.

For each serious candidate, construct:
- bull / base / bear cases;
- entry condition or price structure (not a fabricated exact price);
- invalidation condition;
- expected holding horizon;
- liquidity and execution caveats;
- comparison against keeping the capital in LQDT.

Fundamental quality alone is not an entry signal. Momentum alone is not a sufficient reason to buy. A strong recent return does not prove future positive expectancy.

**Self-check:** Did I select this candidate because it is genuinely attractive, or because I feel obliged to propose a trade? Am I chasing an already extended move? Is the apparent breakout supported by volume and liquidity? What is the counter-thesis?

## 7. Apply the opportunity-cost and trade hurdle

For every proposed trade, compare the position with the best available alternative, including retaining the capital in LQDT.

The comparison must use the same horizon and a consistent basis:
- expected gross price return;
- distributions only when entitlement/date and expected amount are sufficiently established;
- LQDT net return estimate for the same horizon;
- commission, spread, slippage, taxes and other relevant implementation costs;
- volatility, downside/gap risk, liquidity and uncertainty.

Do not claim a precise mathematical expectation unless it is supported by a defined model or historical conditional sample. When only qualitative evidence exists, say so and use ranges or scenario analysis rather than fake precision.

A trade clears the hurdle only if:
1. there is a defined setup or information/catalyst thesis;
2. the expected advantage over LQDT is meaningful after costs;
3. downside and invalidation are understood;
4. the position improves the portfolio rather than merely adding standalone exposure;
5. the evidence quality is sufficient for the proposed size.

If no candidate clears the hurdle, keep the capital in LQDT. This is an active decision to wait, not a failure to make a decision.

**Self-check:** Would I still make this trade if I had no existing position and no pressure to be active? Does the expected edge survive realistic costs? Is the premium large enough to compensate for uncertainty and downside?

## 8. Construct the target portfolio

Start from the validated actual portfolio, not from a preferred target or a historical tactical allocation.

For each position decide whether to hold, add, trim, exit, or open. Then set target weights and calculate percentage-point changes.

Portfolio checks:
- total allocation and treatment of residual cash/assets;
- no more than 10 simultaneously held equity names;
- aggregate signed portfolio loading remains within the user's stated range of -0.5 to +1.5;
- liquidity, spread, concentration, sector overlap and correlated exposures;
- event/gap concentration over the next 1 / 5 / 20 sessions;
- turnover and expected benefit relative to implementation friction;
- whether LQDT remains the superior destination for marginal capital.

The user's aggregate signed loading range is a boundary, not a target. It does not imply a need to use shorts or leverage. No per-security cap or separate gross-exposure cap has been supplied; do not invent either. Do not create an arbitrary minimum equity allocation or use all available portfolio capacity.

Position size must reflect evidence strength, volatility, liquidity, downside, event risk, correlation with existing holdings, and the cost of being wrong. If those inputs do not support a precise weight, provide a conditional range or state why a responsible target cannot yet be set. Do not disguise uncertainty with decimal-place precision.

**Self-check:** Does the proposed portfolio have a better risk/return profile than the current one? Have I counted correlated positions as if they were diversified? Does the total reconcile? Have I accidentally used the current tactical equity sleeve as a strategic baseline?

## 9. Adversarial logic audit — mandatory before finalizing

Run this checklist against the proposed decision:

1. **Mandate:** Did I use the 1 / 5 / 20-session horizons rather than a long-term investment horizon?
2. **Input integrity:** Is the portfolio state reconciled and timestamped? Did I invent any missing holdings or cash?
3. **Data quality:** Are market data current, correctly aligned, and sufficiently covered?
4. **Comparability:** Are stock returns and LQDT returns compared over identical horizons and on a consistent net/gross basis?
5. **Causality:** Have I explained how the evidence could affect price over the selected horizon, rather than merely describing it?
6. **Counterevidence:** Have I actively searched for facts that contradict my preferred action?
7. **Technical validity:** Did I avoid turning SMA, breadth, Z-score, or momentum into deterministic signals without validation?
8. **No anchoring:** Am I preserving a position only because it is already held, or preserving a previous recommendation because I made it?
9. **No action bias:** Am I proposing a trade just to appear useful?
10. **Portfolio effect:** Does the trade improve the whole portfolio after costs and correlated risk?
11. **Arithmetic:** Do target weights, changes, total exposure, and constraints reconcile?
12. **Uncertainty:** Have I marked unknowns and avoided unsupported probability/return precision?

If a check fails, revise the recommendation or explicitly mark the unresolved limitation. Do not silently proceed.

## 10. Qwen second-opinion review

Qwen is an optional adversarial reviewer, not a voting member and not a factual authority. The user runs Qwen manually and supplies its response.

When useful, send it:
- validated portfolio state;
- decision horizons and information cutoff;
- market snapshot;
- the agent's proposed actions and reasoning;
- key evidence and source links;
- unresolved uncertainties.

Ask Qwen to find factual errors, challenge causal links, identify overlooked candidates and risks, and propose an alternative allocation only when justified. It must compare candidates against LQDT on the same horizon.

After receiving its answer:
- verify factual claims against primary sources;
- separate valid objections from unsupported assertions;
- record agreements and disagreements;
- change the recommendation only when evidence or reasoning warrants it.

If no Qwen response is supplied, mark the review as not performed. Do not imply consensus or substitute another LLM.

## 11. Final decision contract

The final answer must contain:

1. **Decision timestamp and information cutoff.**
2. **Incoming portfolio state:** actual weights, total, and missing/partial fields.
3. **Market regime:** concise description with breadth, index, volume/liquidity and volatility evidence available.
4. **Horizon matrix:** 1 / 5 / 20 sessions for the portfolio and each material holding/candidate.
5. **Position decisions:** current weight, target weight, percentage-point change, action, thesis, counter-thesis and invalidation.
6. **New candidates:** only serious candidates; state why each does or does not clear the LQDT hurdle.
7. **Final target allocation:** weights that reconcile to 100% (or explicitly explain any different convention), plus aggregate signed loading and equity-name count.
8. **Execution considerations:** liquidity, spread, costs, event timing and whether the recommendation is conditional.
9. **Scenarios:** bear / base / bull where useful, with assumptions rather than false precision.
10. **Triggers:** observable conditions that would cause reassessment; distinguish validated rules from provisional watch levels.
11. **Confidence:** separately assess confidence in direction, exact sizing, and data quality.
12. **Logic audit:** disclose any failed checks, unresolved unknowns, or reasons for no trade.
13. **Qwen review:** status and material disagreements, if applicable.

Use direct action language. A valid outcome may be HOLD ALL, HOLD SOME / TRIM OTHERS, ROTATE TO LQDT, ADD, or EXIT. Recommendations are not orders.

## 12. Journal and feedback loop

After the user accepts/rejects the recommendation or supplies the executed state:
- preserve the incoming snapshot;
- record the recommendation separately from actual execution;
- record the thesis, evidence cutoff, alternatives rejected, and invalidation conditions;
- later evaluate outcomes over 1 / 5 / 20 sessions;
- compare realized outcome with the decision process and available evidence, not P&L alone;
- record false positives, missed risks, premature exits, opportunity cost, and lessons.

Never rewrite a prior decision to make it appear correct after the fact.

## 13. Current reference state and latest breadth-transfer audit (2026-11-24)

### Actual portfolio snapshot (not execution-confirmed since 2026-11-23)
- T: 10%
- GCHE: 2%
- LQDT: 88%

This is the latest user-reported actual allocation. The 5/2/93 recommendation made earlier on 2026-11-24 was not executed and is superseded by the completed matched-benchmark and walk-forward audit below. Do not represent 5/2/93 as the current portfolio or as the current recommendation.

### Breadth-transfer experiment: user-run results supplied 2026-11-24
Current breadth reference: 8% (4/50 above SMA20; local screener snapshot). Historical diagnostic sample:
- HAC regression, horizon 5: breadth slope +0.00955; t-statistics +2.41 to +2.68 for lags 9-39 (lag 4 t=2.48); nominal p-values 0.007-0.016. This supports a positive association between breadth and subsequent 5-session equal-weight universe returns in this sample. It does not by itself establish a tradable or out-of-sample edge.
- HAC regression, horizon 20: slope +0.00564; t-statistics fall from 1.26 (lag 0) to 0.41 (lag 39); no statistical evidence of a stable linear association at this horizon.
- Matched LQDT comparison in low breadth (0-10%):
  - 5 sessions: n=250; mean equity return -0.143%; mean matched LQDT return +0.187%; mean excess -0.330 percentage points; equity beat LQDT on 45.2% of observations.
  - 20 sessions: n=250; mean equity return +1.378%; mean matched LQDT return +0.897%; mean excess +0.480 percentage points; equity beat LQDT on 48.4% of observations.
  - Returns use the same next-session-open to horizon-close convention for equity and LQDT. These are historical conditional averages, not forecasts or guaranteed outcomes. Transaction costs and uncertainty intervals for the excess means are not supplied.
- Breadth buckets are not monotonic:
  - 5-session low-breadth bucket mean -0.115%, versus +0.183% for breadth above 50%.
  - 20-session low-breadth bucket mean +1.732%, versus +0.410% for breadth above 50%.
  - The 20-session low-breadth bucket is positive, but its median is only +1.012%; bucket means and medians vary materially across regimes.
- Non-overlap timing offsets:
  - At 5 sessions, all five calendar offsets in the low-breadth subset have negative mean returns (approximately -0.01% to -0.53%); each offset has only 51-58 observations.
  - At 20 sessions, most offsets have positive means, but each offset contains only 9-19 low-breadth observations and results are dispersed. This is weak evidence, not a stable timing rule.
- Expanding walk-forward diagnostics:
  - 5 sessions: n=3,349; correlation 0.0356; direction accuracy 53.72%; model MAE 2.0247% versus baseline MAE 2.0211%; model RMSE 2.9985% versus baseline 2.9984%. Low-breadth subset n=183; actual mean +0.230%, predicted mean -0.435%, positive share 53.55%.
  - 20 sessions: n=3,305; correlation -0.1343; direction accuracy 52.74%; model MAE 4.5612% versus baseline 4.5155%; model RMSE 6.2704% versus baseline 6.2187%. Low-breadth subset n=182; actual mean +2.335%, predicted mean +0.415%, positive share 54.95%.
  - The walk-forward model does not add predictive value over the unconditional baseline on MAE/RMSE at either horizon. The 20-session forecast correlation is negative. Do not use this model for allocation.
- Important unresolved diagnostic: the 20-session low-breadth bucket/matched means are positive, while the simple HAC linear model's 20-session slope is statistically insignificant and the walk-forward model underpredicts low-breadth outcomes. These are not necessarily mathematical contradictions (nonlinear/regime mixture and different evaluation subsets can produce them), but they rule out a simple linear "low breadth means sell" interpretation. Audit sample construction, regime persistence, and subset alignment before any stronger claim.
- Historical samples are not independent observations merely because n is large; forward horizons overlap, regimes cluster, and the low-breadth subset is much smaller than the full sample. No block-bootstrap confidence intervals, pre-registered OOS regime rule, T beta/conditional alpha estimate, or GCHE-specific transfer test is supplied.

### GCHE issuer-specific review (2026-11-24; completed after process correction)

GCHE is outside the TOP50 breadth universe. This means only that the TOP50 breadth experiment does not cover it; no inference about its own risk or expected return follows. A separate review was completed using issuer disclosures and market information.

**Fundamentals:** 9M 2026 revenue +6.4%; adjusted gross profit +26.1%; adjusted EBITDA +28.5% to RUB 51.2bn; reported net profit +20.3%; adjusted net profit +135.9% to RUB 24.2bn; adjusted FCF RUB 19.8bn versus RUB 5.2bn; net debt -7.9% to RUB 131.1bn; net debt/adjusted EBITDA 1.9x; interest coverage 3.4x. Positive quality-of-earnings direction, but physical sales -0.3%, exports -10.1%, export average price -5.5%, Foodservice -0.9%. Margin improvement partly relies on pricing/mix, favorable grain procurement, and capex reduction; these may not persist. China export accreditation restrictions and feed-cost reversal are material risks.

**Price/technical:** public market snapshots show GCHE around RUB 3,790 on 23 Nov after +3.67%, then around RUB 3,729 on 24 Nov (-1.61%) with an intraday range roughly 3,683-3,775. The short-term tape is volatile and did not confirm a clean continuation on 24 Nov. External technical sources and local adjusted-price indicators are not perfectly timestamp/price-basis aligned; do not combine them into one synthetic signal.

**Horizon view:** 1 session neutral / elevated event and range risk; 5 sessions neutral due choppy price action despite positive issuer results; 20 sessions moderately positive on improving margins, FCF and leverage, with export/feed-cost risks.

**Decision:** HOLD existing 2%; do not add. The small position is supported by improving issuer fundamentals and no verified thesis-breaking event, but near-term price action is volatile and no validated alpha model or clear LQDT-beating expected-return estimate exists. No cost basis or exact position-level risk budget was supplied, so no claim about unrealized P&L or optimal sizing is made. Reassess on deterioration in export restrictions, feed-cost/margin outlook, interest coverage/debt, cash generation, or a confirmed technical breakdown with volume. An unverified report of a poultry mortality incident is excluded from the base case pending reliable confirmation.

### Decision after completed audit (recommendation, not execution)
**HOLD current portfolio: T 10%, GCHE 2%, LQDT 88%.**
- T: HOLD 10%. Weak breadth is a short-horizon risk warning; matched historical low-breadth equity excess is negative over 5 sessions. However, the effect is modest (-0.33 pp average versus LQDT), beat frequency is 45.2%, walk-forward forecasts fail to beat the baseline, and no T-specific beta/alpha or portfolio-level sizing estimate exists. This is insufficient to justify the earlier arbitrary 5 percentage-point trim. Do not add.
- GCHE: HOLD 2%. It is outside the TOP50 breadth universe; no direct inference from this breadth test is valid. Continue issuer-specific price, event, liquidity and fundamental review. Do not add on this evidence.
- LQDT: retain 88% as the current opportunity-cost alternative. No forced rotation from equities is justified by this experiment alone.
- New positions: 0%. No validated cross-sectional edge or candidate-specific advantage over LQDT has been demonstrated.
- No leverage or shorts recommended. No order was placed; the user retains execution authority.

### Operating implications and reassessment triggers
1. Breadth remains a market-state warning and a reason to avoid adding beta, not an automatic sell signal.
2. For 1-5 session decisions, explicitly price gap/event risk and the modest historical underperformance versus matched LQDT. Reassess if a holding-specific trigger appears; do not convert the market-level result into a mechanical T trade.
3. For 20 sessions, the current evidence does not support a bearish low-breadth rule. Treat the result as mixed/uncertain.
4. Do not use the walk-forward model for forecasts or sizing until it demonstrably beats simple baselines on genuinely out-of-sample data.
5. Before promoting breadth into an allocation rule: verify exact code/sample alignment across bucket, HAC, matched-LQDT and WF outputs; add block-bootstrap or regime-aware uncertainty; test non-overlapping and walk-forward samples; evaluate a pre-specified rule; estimate T-specific beta/alpha and portfolio-level incremental risk; keep GCHE separate.
6. Reassess the HOLD if T-specific price/event evidence deteriorates, if matched LQDT excess becomes robustly negative out of sample after costs, or if the issuer thesis changes. Breadth recovery alone is not an automatic buy trigger.

## 14. Non-negotiable boundaries

- No invented data, prices, weights, constraints, or execution.
- No automatic trades from a single indicator.
- No forced activity or arbitrary minimum equity exposure.
- No treating the key rate as LQDT's exact net yield.
- No mixing 1-, 5-, and 20-session performance windows.
- No treating Qwen's opinion as truth or consensus.
- No silently changing user-approved rules.
- User retains final decision and execution authority.


## 15. Final paired-excess robustness audit and allocation decision (2026-11-25)

### 15.1 Evidence received and estimand

The user supplied the final run of `scripts/one_use/breadth_paired_excess_robustness.py`:
- 5,490 trading-calendar sessions.
- 1,074 LQDT ISS candles in the cached source file; 994 aligned daily returns.
- Thresholds tested in the saved CSV: breadth <=5%, <=10%, <=15%; the console excerpt below is the <=10% slice.
- Forward excess is asset return over sessions t+1..t+h minus LQDT return over the same dates, conditional on breadth at t.
- HAC Newey-West Bartlett lag 20; calendar moving-block bootstrap length 20, 1,000 repetitions; episode bootstrap resamples whole horizon-aware low-breadth clusters.
- The reported intervals are descriptive uncertainty intervals, not predictive intervals and not out-of-sample guarantees.

### 15.2 Read the effective sample correctly

The nominal `n` counts signal dates, not independent market regimes. The script merges low-breadth observations separated by fewer than h sessions, so the total episode count depends on the horizon:
- H1: 111 total episodes.
- H5: 63 total episodes.
- H20: 47 total episodes.

The number of episodes actually represented in each complete-case sample is much smaller:
- T: H1 14; H5 7; H20 4.
- GCHE: H1 26 asset-specific / 14 common; H5 17 / 7; H20 10 / 4.
- EW-TOP50: same complete-case counts as GCHE in this run.

The episode bootstrap is deliberately unavailable when fewer than 10 valid clusters remain. `NA` is a sample-size warning, not a zero effect and not a software failure. In particular, H20 common-date inference is based on only four valid episodes for every series. The H20 common-date GCHE HAC interval excluding zero is not sufficient evidence by itself because its calendar-block interval includes zero and episode bootstrap cannot be estimated.

The episode grouping rule (merge low-breadth observations separated by fewer than h sessions) is a defensible way to reduce overlap-induced pseudo-replication, but it is one operational definition, not a uniquely correct partition of market regimes. Results should not be described as having 14, 17, or 26 independent economic regimes without qualification.

### 15.3 Results at breadth <=10%

All returns and intervals below are percentage points of forward excess versus matched LQDT.

| Asset / horizon | Sample | n dates | Valid episodes | Mean excess | HAC 95% | Calendar block 95% | Episode bootstrap 95% |
|---|---:|---:|---:|---:|---:|---:|---:|
| T H1 | asset/common | 60 | 14 | +0.161% | [-0.257, +0.578] | [-0.235, +0.652] | [-0.118, +0.538] |
| T H5 | asset/common | 60 | 7 | +0.610% | [-1.069, +2.289] | [-1.084, +2.606] | NA |
| T H20 | asset/common | 58 | 4 | +0.504% | [-3.880, +4.889] | [-3.251, +7.694] | NA |
| GCHE H1 | asset-specific | 123 | 26 | -0.188% | [-0.453, +0.077] | [-0.473, +0.104] | [-0.391, +0.029] |
| GCHE H1 | common | 60 | 14 | -0.313% | [-0.639, +0.013] | [-0.650, +0.061] | [-0.621, +0.029] |
| GCHE H5 | asset-specific | 123 | 17 | -0.156% | [-1.493, +1.181] | [-1.474, +1.307] | [-1.363, +1.265] |
| GCHE H5 | common | 60 | 7 | -1.245% | [-2.853, +0.363] | [-3.041, +0.596] | NA |
| GCHE H20 | asset-specific | 123 | 10 | -0.918% | [-4.548, +2.713] | [-4.348, +2.790] | [-4.185, +3.670] |
| GCHE H20 | common | 58 | 4 | -4.103% | [-7.204, -1.002] | [-6.513, +0.076] | NA |
| EW H1 | asset-specific | 123 | 26 | -0.117% | [-0.445, +0.211] | [-0.429, +0.257] | [-0.331, +0.189] |
| EW H1 | common | 60 | 14 | -0.139% | [-0.500, +0.222] | [-0.506, +0.330] | [-0.316, +0.113] |
| EW H5 | asset-specific | 123 | 17 | +0.022% | [-1.035, +1.079] | [-1.070, +1.148] | [-0.642, +0.943] |
| EW H5 | common | 60 | 7 | -0.298% | [-1.839, +1.244] | [-1.954, +1.483] | NA |
| EW H20 | asset-specific | 123 | 10 | +0.210% | [-3.076, +3.496] | [-2.929, +3.733] | [-2.544, +4.554] |
| EW H20 | common | 58 | 4 | -1.800% | [-5.393, +1.792] | [-5.016, +3.385] | NA |

### 15.4 Statistical interpretation

**T**
- Mean excess is positive at all three horizons, but every available interval includes zero.
- H5 and H20 have only 7 and 4 valid horizon-aware episodes; the episode bootstrap is unavailable.
- Positive mean is not evidence of a stable conditional premium. H20 median is negative (-1.379% in the supplied run), so the positive mean is not representative of the typical observation.
- This analysis does not prove that T underperforms LQDT; it also does not establish that T beats LQDT.

**GCHE**
- Point estimates are negative at all horizons.
- H1 intervals include zero, although the episode-bootstrap upper bounds are close to zero.
- H5 asset-specific intervals are broad and include both material underperformance and outperformance. Common-date sample has only seven valid episodes.
- H20 asset-specific intervals include zero. Common-date HAC is negative, but calendar-block upper bound is +0.076% and only four valid episodes remain. Treat this as a warning, not robust evidence for EXIT.
- GCHE is outside the TOP50 universe; the EW breadth series is not a substitute for issuer-specific alpha or beta.

**EW-TOP50**
- No horizon shows a robust excess-return result across the uncertainty methods.
- H1/H5 estimates are near zero; H20 is highly dispersed and common-date sample has only four valid episodes.
- This experiment does not validate a low-breadth market-timing rule.

**Overall statistical conclusion:** no statistically robust, episode-stable premium or penalty versus LQDT is established for T, GCHE, or EW-TOP50 at <=10% breadth. The evidence is especially weak at H20. It is incorrect to convert the negative GCHE H20 common-date mean into a deterministic exit rule, or the positive T means into a holding/adding signal.

### 15.5 Additional data and inference caveats

1. The output uses complete-case samples that differ by asset and horizon. Asset-specific and common-date estimates answer different questions; do not compare their means without acknowledging sample composition.
2. The large difference between GCHE H5/H20 asset-specific and common-date means is a sample-composition warning. It is not resolved by selecting whichever estimate supports a preferred action.
3. The episode bootstrap has few clusters and is unavailable for many rows. Even when available, it is descriptive and assumes the horizon-aware clusters are suitable resampling units.
4. The moving-block bootstrap uses 20-session blocks. This is a sensitivity check, not proof that all dependence structures are captured.
5. The supplied console output does not show the <=5% and <=15% rows. Those are in the CSV but were not included in this final verbal interpretation. Do not claim threshold robustness until those rows are inspected.
6. The current breadth reference from the preceding user snapshot was 8% (4/50); the current signal is a warning about narrow participation, not a standalone action.
7. LQDT's trailing return is floating. A 25 Nov market-data comparison reported 30-day annualized return 14.56% and 90-day annualized return 14.65%; these are backward-looking, not a guaranteed forward rate. The actual matched historical LQDT returns in the user's ISS series remain the correct benchmark for this backtest.
8. The local script output is user-run evidence. No claim is made that the agent independently executed the local repository code.

### 15.6 Issuer-specific refresh and horizon assessment

**T / T-Technologies**
- Official company page lists October 2026 operating results dated 24 Nov and 3Q IFRS results dated 10 Nov.
- October operating data reported by the company: loan portfolio +25% YoY to RUB 4.2tn; business loans +62%; client funds plus brokerage assets +5% to RUB 6.5tn; client funds on accounts alone RUB 3.9tn, down 9% YoY and 3.6% MoM; investment assets +34% YoY. The October bank profit figure of RUB 160.5bn is RAS bank profit, not consolidated IFRS group profit. Do not conflate the two.
- The funding-mix divergence (credit portfolio growth against falling customer account funds) is a monitoring risk. It does not by itself prove a funding crisis, but it weakens an unconditional bullish thesis. The 9M operating net profit growth and raised guidance remain positive counterevidence.
- The group has strategic transaction/execution complexity, including CIAN and Tochka-related actions. Monitor dilution, capital allocation, and execution.
- 25 Nov quote feeds showed inconsistent intraday values/time stamps. A public quote snapshot at 18:00 reported RUB 279.50 and a weekly decline of 4.33%; another source earlier in the day showed materially different levels. Treat the exact price/technical state as provisional pending the user's local aligned snapshot.
- Horizon view: H1 neutral; H5 neutral to cautious because funding mix and price weakness offset growth; H20 constructive but conditional on credit quality, funding stability, capital adequacy, and transaction execution.
- Decision: HOLD existing 10% provisionally; do not add. No evidence in this breadth audit supports a trim or an add. This is not a claim that 10% is an optimized weight. Reopen if customer funding continues to deteriorate relative to loan growth, credit costs/NPLs rise, capital adequacy weakens, guidance is cut, or a confirmed price/liquidity deterioration appears.

**GCHE / Cherkizovo**
- Official 9M 2026 disclosure (17 Nov): revenue +6.4%; adjusted gross profit +26.1%; adjusted EBITDA +28.5% to RUB 51.2bn; adjusted net profit RUB 24.2bn versus RUB 10.3bn; adjusted FCF RUB 19.8bn versus RUB 5.2bn; net debt RUB 131.1bn; net debt/adjusted EBITDA 1.9x; interest coverage 3.4x.
- Offsetting risks: physical sales -0.3%; exports -10.1%; foodservice -0.9%; transport expenses +10.4%; improved margins partly depend on favorable grain procurement/pricing and lower capex. Reduced capex may limit capacity growth if sustained. Export restrictions and high interest burden remain material.
- 25 Nov external quote feeds were inconsistent in time/price; no single quote is treated as authoritative. The local adjusted-price and liquidity snapshot is still needed for a fully timestamp-aligned technical review.
- Horizon view: H1 neutral; H5 neutral/cautious; H20 moderately constructive on cash generation and deleveraging, offset by export, demand, feed-cost and capex risks.
- Decision: HOLD existing 2% provisionally; do not add. Breadth statistics do not cover GCHE directly and do not support EXIT. No robust LQDT-beating expected return has been demonstrated, so the small position is retained only while the issuer thesis remains intact, not because ownership itself is a reason to hold.

### 15.7 Full decision path

```text
START
 |
 |-- Validate actual portfolio snapshot
 |     |-- stale/partial/weights unreconciled -> mark state provisional; no execution claim
 |     '-- latest user-reported: T 10 / GCHE 2 / LQDT 88 (not re-confirmed after 23 Nov)
 |
 |-- Freeze data and market state
 |     |-- breadth 8% -> narrow participation warning
 |     '-- never convert breadth threshold directly into BUY/SELL/weight
 |
 |-- Evaluate paired asset-minus-LQDT history
 |     |-- date-matched? yes
 |     |-- overlapping windows / clusters handled? partly, via HAC + 20d blocks + episode clusters
 |     |-- enough valid episodes? H20 often no
 |     '-- robust premium/penalty across methods? no
 |           '-- breadth experiment cannot force trim/exit/add
 |
 |-- Review each holding independently
 |     |-- T: issuer thesis broadly constructive, funding mix is key risk,
 |     |      short-horizon price state not fully aligned -> HOLD 10%, no add
 |     '-- GCHE: improved FCF/profitability and leverage, operating/export risks,
 |            no direct TOP50 coverage -> HOLD 2%, no add
 |
 |-- Review new candidates
 |     '-- no candidate with verified after-cost premium vs LQDT -> 0% new equity
 |
 '-- Portfolio-level decision
       '-- HOLD 10 / 2 / 88; no leverage/shorts; no order placed
```

### 15.8 Final recommendation (25 Nov 2026; recommendation, not execution)

**HOLD / NO CHANGE: T 10%, GCHE 2%, LQDT 88%; new positions 0%.**

This is a provisional, evidence-conservative decision, not a mathematically optimized target:
- T 10%: HOLD; no add and no breadth-driven trim. Positive fundamentals are offset by funding-mix and transaction risks; matched excess intervals do not establish an edge either way.
- GCHE 2%: HOLD; no add and no breadth-driven exit. The fundamental thesis remains positive but conditional; low-breadth common-date H20 warning is too cluster-sparse and method-sensitive to dictate exit.
- LQDT 88%: retain. Its trailing 30-day annualized return was about 14.56% as of 25 Nov, but the rate floats and must not be treated as a forward guarantee.
- New equities: 0%. No candidate has a verified after-cost advantage over LQDT.
- No leverage or short positions recommended. No order placed; the user retains execution authority.

Why not trim T to 5% or exit GCHE? Neither exact sizing follows from the supplied data. The breadth test does not estimate an optimal portfolio weight, T-specific conditional alpha, or GCHE-specific risk. A forced reduction would create false precision. Why not add? No validated expected-return premium over the floating LQDT hurdle is demonstrated.

### 15.9 Self-audit and failure disclosure

- Portfolio state: latest known weights are from 23 Nov; no newer user-confirmed executed state supplied. PASS with stale-state qualification.
- Market breadth: latest prior local snapshot 8% (4/50); current threshold is not an order rule. PASS.
- LQDT benchmark: actual ISS price series is separately sourced and date-aligned; 994 daily returns available from 1,074 candles. PASS for the supplied sample, but coverage is not complete across the full 5,490-session calendar.
- Horizon matching: forward windows t+1..t+h matched for asset and LQDT. PASS as defined by script.
- Dependence: HAC, 20-session moving blocks, horizon-aware episode clusters used. PARTIAL; H20 cluster counts too low for reliable episode bootstrap.
- Multiple thresholds: 5/10/15% generated in CSV, but console excerpt supplied only <=10%. NOT FULLY VERIFIED in this final review.
- Common-date integrity: sample sizes differ materially from asset-specific; the output quantifies this but does not explain every excluded date. PARTIAL.
- Issuer-specific evidence: T and GCHE have recent fundamental reviews; 25 Nov quote feeds conflict and local timestamp-aligned price/volume snapshot is unavailable. PARTIAL.
- Valuation and expected-return hurdle: no current intrinsic valuation / forward expected return distribution for T or GCHE. NOT ESTABLISHED.
- Portfolio optimization: no covariance-based marginal risk contribution or expected-return optimizer supplied. Exact weights are NOT OPTIMIZED.
- Candidate search: no fresh full candidate universe audit in this final cycle. No new position is approved; broader candidate ranking remains NOT FULLY REASSESSed.
- Qwen: no fresh Qwen opinion supplied for this cycle. NOT PERFORMED.
- Execution: no order placed or assumed. PASS.

**Final confidence:** high that this breadth experiment does not justify an automatic action; moderate that no new equity should be added; low-to-moderate in retaining exact existing weights; low in any claim that 10/2/88 is optimal. If a fully refreshed local quote/volume snapshot, <=5/15% CSV rows, or new issuer disclosure changes the evidence, reopen the relevant branch rather than rewriting this decision retroactively.
