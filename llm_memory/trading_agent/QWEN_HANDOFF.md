# Qwen Handoff

Last updated: 2026-11-25

## Purpose

Adversarially review the current daily trading decision. Qwen is a critic, not a vote, signal source, or authority. The independent analysis must be completed before this handoff is prepared.

## Current operating protocol

Canonical source: [06_DAILY_TRADING_RESEARCH_LOOP.md](06_DAILY_TRADING_RESEARCH_LOOP.md).

The question is: **what should be LONG or SHORT today, on which horizon, and at what justified size?**

- Daily input: final actual-portfolio, SBMX, and LQDT results.
- First audit the previous decision, counterfactual opportunity cost, and realized outcome.
- Generate falsifiable hypotheses and inspect current market/price data plus relevant semantic information.
- Build a decision tree and self-check every branch.
- Exclude arguments that fail self-check.
- One-use scripts: at most two passes before this review (first run, result analysis).
- After this review: at most two further script passes (first run, result analysis).
- Commit every material branch/leaf of the decision tree.
- Active actions are LONG or SHORT. Never use HOLD.
- LONG LQDT is the neutral opportunity-cost allocation when no equity LONG/SHORT has sufficient evidence.
- Every risky position size must be justified by expected edge, uncertainty, downside, covariance, liquidity, costs, and portfolio constraints.
- Do not use prior ownership or small position size as a reason to retain exposure.

## What Qwen must challenge

1. Is the proposed directional edge real, point-in-time valid, and stronger than LQDT after costs?
2. Are data, labels, dates, horizons, and benchmarks aligned?
3. Is the hypothesis falsifiable, or is it a narrative fitted after observing the outcome?
4. Are sample size, dependence, regime clustering, and uncertainty handled honestly?
5. Does the proposed size follow from the evidence and risk, or is it arbitrary?
6. What alternative LONG/SHORT instruments or neutral LONG LQDT allocation were omitted?
7. What would invalidate the thesis, and where does the reasoning exceed its validated boundary?
8. Which decision-tree branches are unsupported and should be removed?

Return:
- strongest objections;
- missing tests/data;
- factual claims requiring source verification;
- alternative directional hypotheses;
- sizing critique;
- explicit verdict on each branch: survives / revise / reject.

Do not simply agree or produce a generic bear/base/bull essay. Challenge the actual evidence and decision path.

## Historical context warning

Earlier 2026-11-24 material recommended HOLD T/GCHE and is archived. It is not current policy or an active recommendation. Do not anchor on historical weights. Current actual positions must come from the user's latest snapshot.

## Reviewer boundary

The user submits this packet to Qwen and returns its response. The assistant does not claim direct Qwen API access. The assistant independently adjudicates Qwen's objections against source evidence and the self-check protocol.
