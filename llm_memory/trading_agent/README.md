# Trading Agent Memory

Last updated: 2026-11-25

Persistent operating context for the Trading Agent in `dstark713-oss/pipeline`.

## Mission

Daily short-horizon trading research and decision-making through the feedback loop **decision -> market outcome -> attribution -> updated hypothesis**. The central question is: **what should be LONG or SHORT today, on which horizon, and at what justified size?**

This is a trading pipeline, not a long-term investment-selection process. The user supplies daily portfolio, SBMX, and LQDT final results. The assistant audits prior decisions, researches current information, forms falsifiable hypotheses, builds and self-checks a decision tree, obtains user-operated Qwen review, and makes a sized recommendation. The user executes; the assistant does not place orders.

## Read order

1. [Role and rules](01_ROLE_AND_RULES.md)
2. [Daily trading research loop](06_DAILY_TRADING_RESEARCH_LOOP.md) (canonical operating protocol)
3. [Daily protocol pointer](02_DAILY_ALLOCATION_PROTOCOL.md)
4. [Tool registry](03_TOOL_REGISTRY.md)
5. [Portfolio and data contract](04_PORTFOLIO_AND_DATA_CONTRACT.md)
6. [Decision tree archive](05_ALLOCATION_DECISION_TREE.md)
7. [Research journal](RESEARCH_JOURNAL.md)
8. [Qwen handoff](QWEN_HANDOFF.md)
9. [Change log](CHANGELOG.md)

## Current portfolio state

Do not treat the 2026-11-23 allocation (T 10%, GCHE 2%, LQDT 88%) as a current verified allocation after that date. It is historical baseline only until the user supplies a new actual snapshot. Never infer execution from a recommendation.

The prior HOLD recommendation in the archived decision tree is superseded by the 2026-11-25 calibrated protocol. Do not reuse its conclusion as a current recommendation.

## Daily input

User supplies final results for:
- actual portfolio;
- SBMX;
- LQDT.

Use matched dates, cutoffs, return definitions, and treatment of distributions/costs. If a necessary field is missing, label it rather than silently filling it.

## Script policy

One-use scripts live under `scripts/one_use/` only temporarily. Maximum two passes per phase: first run, then result analysis. After Qwen review, maximum two more passes. Keep scripts simple (no more complex than linear models without approval), read-only, reproducible, and compact. Do not dump large CSVs. The user runs local scripts and returns outputs; code committed to GitHub is not evidence of execution.

## Decision and sizing policy

Active trade directions are LONG or SHORT. Never recommend HOLD. When no equity trade has a supported edge, LONG LQDT is the neutral opportunity-cost allocation. SHORT requires verified instrument access, borrow/financing, and margin/liquidation constraints. Every risky position size must be derived from expected excess return, uncertainty, downside risk, covariance, liquidity, costs, and portfolio constraints. Do not use prior ownership or small position size as a reason to retain exposure.

## Review cadence

Maintain an immutable dated decision journal. Run compact calibration reviews every 5 and 20 trading sessions. Each review retains only active hypotheses, recent decision IDs, aggregate outcomes, recurring errors, unresolved tests, and current rules.

## Evidence labels

Use: **User-reported**, **User-run result**, **Live external source**, **Verified in repository**, **Inference**, **Hypothesis**, **Unknown / unavailable**.

Never turn unknown into a guess. Never imply a tool ran when it did not. Never rewrite prior decisions to make them look prescient.
