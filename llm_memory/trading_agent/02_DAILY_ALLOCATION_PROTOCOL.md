# Daily Allocation Protocol

Last updated: 2026-11-24

## Trigger

User message: **"Аллокация на сегодня"** or an unambiguous equivalent.

The goal is to train and improve the agent's real-market allocation reasoning through a repeated human-in-the-loop cycle. This is not an API-orchestration project.

## Phase 0: Establish the decision frame

1. Establish the decision date, market session, and relevant data cutoff.
2. Read the latest known allocation ledger from this memory and the user's latest updates.
3. Read [the allocation decision tree and current decision](05_ALLOCATION_DECISION_TREE.md).
4. Request the **Daily Market Snapshot** from the user: current local screener/market breadth outputs and any other relevant local research results. Ask only for the missing items needed for today's decision.
5. If the user supplies a new portfolio snapshot/allocation, reconcile it against the ledger. Do not infer that unreported allocation is cash.
6. Mark stale or missing data explicitly.

## Phase 1: Daily Market Snapshot

The user supplies the local outputs. The agent must not claim to execute local scripts or inspect local files unless those outputs are actually attached or pasted.

When requesting outputs, provide the exact filenames or commands based on the current repository state. Prefer asking for already-generated valid outputs over forcing unnecessary reruns. Interpret coverage, data dates, missingness, and known limitations before relying on the numbers.

## Phase 2: News and fundamentals (agent responsibility)

Independently research current information for current holdings and serious candidates:
1. Search current issuer, sector, macro, regulator, and corporate-event news over a relevant window.
2. Prefer primary sources: issuer disclosures, MOEX, regulator notices, official filings, company reports, court/regulatory records.
3. Use reputable media for discovery and context, not as a substitute for primary facts.
4. Capture event date, publication date/time, retrieval time, issuer/instrument, source link, and whether the item is genuinely new or repeated.
5. Search adverse developments and contradictory evidence, not only bullish headlines.
6. Deduplicate syndicated/repeated coverage. Copies of one announcement are one event.

Fundamental review should use the latest comparable reported facts:
- revenue, operating profit/EBITDA where meaningful, net income;
- operating/free cash flow and capex;
- net debt, liquidity, debt maturities and interest burden;
- margins and direction;
- dividend policy, declared dividends, payout and dates;
- guidance, management changes, dilution, buybacks, capital raises, governance, regulation, sanctions, litigation, and other material events;
- valuation only with explicit reporting period, denominator, and methodology.

Respect issuer differences. Do not compare bank and industrial-company ratios as if interchangeable. Separate IFRS/RAS and reported/adjusted metrics. A good company is not automatically a good investment at any price.

## Phase 3: Semantic reasoning (agent responsibility)

The semantic engine is the LLM's reasoning, not a separate software component. For each material event or narrative:
- identify what actually changed versus the prior state;
- assess novelty, recency, source credibility, and proximity to primary evidence;
- map direct and indirect issuer/sector exposure;
- explain the transmission channel into earnings, cash flow, debt, liquidity, risk, valuation, or expectations;
- estimate likely horizon (intraday, weeks, quarters, structural);
- identify uncertainty, alternative explanations, and counterevidence;
- distinguish a real information shock from recycled news or market noise.

Do not reduce this to generic sentiment. State the strongest competing interpretation.

## Phase 4: Independent thesis before Qwen

Before reading Qwen's response where practical, record:
- the agent's initial view of each material holding;
- the strongest bear and bull cases;
- what evidence would change the view;
- whether the position's current weight appears justified.

This prevents Qwen from anchoring the agent's first conclusion and makes disagreements informative.

## Phase 5: Qwen review (user-operated for now)

Qwen is the only second-opinion LLM. The agent prepares a focused prompt and evidence packet; the user submits it to Qwen and returns the answer.

Ask Qwen to:
1. identify missing information and unsupported assumptions;
2. challenge the causal chain from event to issuer value;
3. give strongest bear/base/bull counterarguments;
4. identify tail risks, crowded narratives, and confirmation bias;
5. state what evidence would change its view.

Then verify factual claims, compare reasoning, and record agreements/disagreements. Qwen is not a vote, authority, or source of facts. If no Qwen response is supplied, mark review as pending and continue without pretending it happened.

## Phase 6: Allocation synthesis

Use the current user-provided allocation as the baseline. For each position/candidate, explain:
- current and proposed weight;
- change in percentage points;
- action: hold / add / trim / exit / not assessable;
- deterministic market state, if supplied;
- news/fundamental thesis;
- strongest counterargument;
- confidence and invalidation condition.

Portfolio-level constraints explicitly supplied by the user:
- no more than 10 simultaneous equity names;
- aggregate signed portfolio loading from -0.5 to +1.5;
- no per-security weight limit has been supplied;
- no separate gross-exposure limit has been supplied.

Do not invent missing constraints. The aggregate loading range is not a per-security cap. It permits short exposure and leverage mathematically but does not make either desirable by default.

Portfolio-level checks:
- state the allocation convention and make the total explicit;
- do not classify unknown weight as cash;
- consider liquidity, spread, turnover, taxes, and transaction costs where evidence exists;
- avoid churn when expected benefit is smaller than implementation friction;
- if inputs do not support precise weights, provide a bounded/conditional recommendation or request the one missing critical input.

A no-change decision is a valid result. Recommendations are not orders.

## Phase 7: Report and journal

Report in this order:
1. Executive allocation view.
2. Current baseline and missing portfolio data.
3. Daily Market Snapshot status and market regime.
4. Position-by-position analysis.
5. News and fundamentals.
6. Independent semantic thesis and counter-thesis.
7. Qwen review and disagreements, if available.
8. Proposed allocation and changes.
9. Risks, invalidation conditions, and confidence.
10. Journal entry and next observation to track.

Record the initial thesis, final recommendation, alternatives rejected, Qwen contribution, and later outcome/lesson. Do not rewrite old decisions to make them look prescient.

## Research gap escalation

If a required input or diagnostic is absent from the current tools and cannot be reliably obtained from public sources:

1. State the precise research question and why its answer may change the investment decision.
2. Identify the local source needed (database/table/file/API/cache) and the minimum fields/time range.
3. Write a complete, one-off Python script under `scripts/one_use/` when practical. Include a repository-relative path comment at the top of the file.
4. Default to read-only access; do not mutate production databases or canonical datasets. Use bounded queries and explicit output paths.
5. Tell the user exactly how to run it and which output file/console section to return. The user may also pull the committed script from GitHub and run it locally.
6. Analyze the actual returned result. Until then, mark the question unresolved and the script as not yet run.

When Codex/Python access becomes available, use accessible project files directly for analysis where permitted. Until then, user-run scripts are the handoff mechanism. Do not confuse a planned future capability with current access.
