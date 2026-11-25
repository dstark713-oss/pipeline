# Daily Trading Research Loop

Last updated: 2026-11-25

## Mission

Train a repeatable short-horizon trading decision process through the daily loop **decision -> market outcome -> attribution -> updated hypothesis**. The central question is:

**What should be LONG or SHORT today, on which horizon, and at what justified size?**

This is a trading pipeline, not a long-term investment-selection process. Fundamental information is included only when it can affect price, event risk, liquidity, or the probability distribution over the active trading horizons. It must not displace market/price evidence or become a generic company-quality review.

## Daily input

The user supplies final daily results for:
- the actual portfolio;
- SBMX benchmark;
- LQDT opportunity-cost benchmark.

Reconcile date, close/cutoff, total return convention, fees/taxes if known, distributions, and actual position weights. Never compare mismatched dates or price-return and total-return series without explicit adjustment.

## Required daily cycle

### 1. Outcome and decision audit

Before forming a new view:
- retrieve the previous decision snapshot, thesis, direction, horizon, sizing rationale, invalidation, and expected path;
- compare realized portfolio, SBMX, and LQDT results on matched dates;
- attribute P&L to market direction, instrument-specific movement, sizing, costs, and timing where data permits;
- compare the result with the counterfactual alternatives that were available at the time;
- identify whether the error was data, hypothesis, model, sizing, execution, or luck;
- record what changed in the reasoning and what remains unresolved.

Do not grade a decision solely by whether it made money. Grade the process against information available at decision time and the realized outcome. Do not excuse poor process because the position was small.

### 2. Hypothesis generation

Every run must produce explicit, falsifiable hypotheses. Each hypothesis states:
- instrument/universe and direction;
- horizon (H1/H5/H20 or a justified alternative);
- expected edge versus LQDT and, where useful, SBMX;
- mechanism and supporting observations;
- strongest opposing explanation;
- observable invalidation;
- evidence required to size the trade.

No hypothesis is carried forward by inertia. Re-test it against the current snapshot.

### 3. Semantic review

Inspect current relevant information and its semantics:
- what is genuinely new versus already priced/repeated;
- source quality and event timing;
- direct/indirect exposure and transmission channel to price;
- horizon, uncertainty, alternative interpretations, and counterevidence;
- whether the information changes the existing hypothesis or only adds narrative.

Fundamentals are conditional inputs, not the default centre of analysis. Do not use company quality as a substitute for a tradable price edge.

### 4. Tools and scripts

Use existing tools first. Create a one-use script only for a specific unresolved question whose answer can change the decision.

Hard limit per research phase: **two script passes total**:
1. first run / data production;
2. result analysis / one correction or follow-up calculation.

No third pass. If the result remains incomplete or the script is invalid, mark the evidence unusable and proceed only with what passed self-check, or state that a defensible directional trade cannot be established.

One-use scripts:
- must be simple, preferably descriptive statistics or linear models; no complexity beyond a linear model without explicit user approval;
- read-only by default;
- have fixed inputs, date cutoffs, reproducible parameters, bounded output;
- produce compact summaries, not giant CSV dumps;
- must generate at least one new falsifiable hypothesis or explicitly explain why no new hypothesis emerged;
- are not permanent pipeline components by default.

### 5. Decision tree and self-check

Build the decision tree from the current data, not by copying yesterday's path. Commit every material branch/leaf of the decision tree to GitHub. Each branch must identify its evidence, assumptions, tests, and resulting action.

Self-check every reasoning argument:
- temporal alignment and point-in-time validity;
- survivorship/look-ahead/data leakage;
- matched benchmark dates and return definitions;
- overlapping horizons and dependent observations;
- sample size, regime concentration, uncertainty and robustness;
- transaction costs, liquidity, borrow/short availability and financing for SHORT;
- model baseline, calibration, and out-of-sample limits;
- whether the evidence actually supports direction and size;
- whether a claim is merely narrative or inherited from a prior decision.

Any argument that fails self-check is removed from the decision rationale, not softened into a caveat and retained as support. Distinguish invalid evidence from valid but weak evidence.

### 6. Qwen adversarial review

Prepare a compact evidence packet and send the proposed decision tree and draft trade to Qwen via the user. Qwen must challenge assumptions, identify omitted alternatives, test causal links, question the sizing, and propose falsification tests.

Do not anchor the independent view on Qwen. Do not average opinions. Verify Qwen's factual claims. Record which objections survive and which fail.

### 7. Post-Qwen verification

After Qwen review, perform at most two further script passes:
1. first run for a genuinely necessary post-review test;
2. analysis of that result.

Do not reopen already-settled analysis without a specific falsifiable reason. If a post-Qwen script cannot pass its self-check within two passes, discard its unsupported claims.

### 8. Final decision

The decision vocabulary for active positions is **LONG** or **SHORT**. Never use HOLD as an action.

- LONG means positive signed exposure with an explicit instrument, horizon, entry condition, invalidation, and size.
- SHORT means negative signed exposure with verified borrow/derivative access, financing, margin/liquidation constraints, and explicit risk limits.
- LQDT is the default LONG opportunity-cost destination when no equity LONG or SHORT has a sufficiently supported positive expected edge. It is not labelled idle cash.
- Do not force a risky equity trade merely to produce activity. Choosing LONG LQDT is a real capital-allocation decision.
- If the user later specifies that LQDT itself is not an acceptable neutral allocation, clarify the permitted neutral state before making a directional commitment.

Sizing is mandatory and must be derived from evidence:
- expected excess return versus LQDT over the stated horizon;
- uncertainty / forecast error and downside distribution;
- volatility and covariance with existing exposures;
- liquidity, spread, turnover, capacity and implementation costs;
- portfolio signed-exposure constraints and actual available capital;
- robustness and confidence of the underlying evidence.

Never choose size because a position is already small, because the user previously owned it, or because a round percentage feels conservative. If the inputs do not justify a nonzero risky size, assign zero to that instrument and allocate the capital to LONG LQDT. Never invent per-name or gross exposure limits.

The output must include: direction, instrument, horizon, target signed weight, change from actual weight, sizing derivation, expected excess versus LQDT, main risk, invalidation, confidence, and what would change the decision. Recommendations are not orders; the user executes.

## Learning and review loop

Maintain a decision journal with immutable dated entries:
- information/data snapshot and cutoff;
- hypotheses considered and rejected;
- tree branches and commits;
- pre-Qwen independent view;
- Qwen objections and adjudication;
- final LONG/SHORT allocation and sizing derivation;
- actual execution if user reports it;
- H1/H5/H20 realized outcome versus LQDT and SBMX;
- attribution, process error, and revised hypothesis.

Run compact reviews every 5 and 20 trading sessions:
- use a compressed context containing only current rules, active hypotheses, recent decision IDs, aggregate outcomes, recurring errors, and unresolved tests;
- review calibration, hit rate, excess return, drawdown, sizing error, missed opportunities, and regime boundaries;
- separate skill from luck and avoid optimizing on tiny samples;
- retire hypotheses that fail, narrow their applicability, or design a new falsification test.

If the current run introduces no new evidence, no changed logic, and no closure of a known gap, explicitly restart the analysis from raw current inputs rather than copying the previous conclusion.

## Evidence and authority

Labels: User-reported, User-run result, Live external source, Verified in repository, Inference, Hypothesis, Unknown.

The assistant researches and recommends. The user supplies local daily results and Qwen review, and remains the final decision-maker. No brokerage execution is authorized or claimed.
