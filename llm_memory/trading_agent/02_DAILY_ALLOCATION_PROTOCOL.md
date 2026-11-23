# Daily Allocation Protocol

Last updated: 2026-11-23

## Trigger

User message: **"Аллокация на сегодня"** (or an unambiguous equivalent).

The agent interprets this as a request to run the full daily research and allocation workflow, not merely to comment on the market.

## Phase 0: Establish the decision frame

1. Obtain the current date/time and timezone relevant to the portfolio/market session.
2. Establish the intended decision point: before open, during session, or after close. If unclear and it changes the data cutoff materially, ask one direct question.
3. Identify the latest completed MOEX session and the as-of dates of all local outputs.
4. Load the latest available portfolio snapshot and constraints. If absent/stale, request the exact required export; do not calculate target weights from memory.
5. Record the baseline portfolio weights, cash, and uninvested allocation.

## Phase 1: Deterministic market-state layer

Expected sequence, subject to freshness and successful prior runs:

1. Refresh MOEX data:
   `python scripts/dataset/fresh/refresh_pipeline.py`
   - This is the current refresh entry point in the repository.
   - It appends raw observations and rebuilds adjusted data and PIT TOP50 panel.
   - It is code-inspected but its latest local runtime status must be confirmed by the user.
   - It does not backfill SECID/board pairs with no existing raw observations.
2. Build current primitive feature frame if missing or behind the latest panel date:
   `python scripts/experiments/primitives/05_build_primitive_features.py`
   - Verify this path and prerequisites in the current repository before issuing it.
3. Run the state screener:
   `python scripts/tools/01_primitive_screener.py`
   - Optional manual position inspection:
   `python scripts/tools/01_primitive_screener.py --inspect`
   - Outputs:
     - `data/interim/screener/latest_primitive_snapshot.csv`
     - `data/interim/screener/latest_market_breadth.csv`
4. User returns console output and/or output files. Check panel date, feature date, coverage, missingness, and refresh status before interpreting.
5. Never run a refresh unnecessarily if a valid current run already exists. Ask for the latest summary/output when freshness is uncertain.

### Deterministic state interpretation

Approved instrument primitives:
- `drawdown_60`: proximity to rolling 60-session high; closer to zero means nearer the high.
- `zscore_sma20_20`: standardized distance from SMA20; positive means above SMA20.
- `realized_vol_60`: trailing realized volatility, descriptive risk state, not a forecast.

Separate market context:
- `breadth_change_5`: 5-session change in the share of valid PIT TOP50 members above SMA20.
- `breadth_sma20`: reference level of that share.

Do not invent additional features, rank the whole market by a composite score, or reinterpret the screener as a buy/sell engine.

The user-proposed breadth exposure heuristic is:
- breadth >= 50% and rising: 100%;
- breadth >= 50% and flat/falling: 75%;
- breadth < 50% and rising: 50%;
- breadth < 50% and flat/falling: 25%.

This is an application heuristic, not a statistically optimized risk model. It may be considered as a separate exposure context, not treated as a validated mandate. There is a known boundary mismatch in a portfolio experiment: code used >50%, while the approved definition is >=50%. Resolve before relying on that experiment's exact 50% classification.

## Phase 2: News and event research

For every material current holding and any serious candidate:
1. Search current news over a relevant window, initially 7-30 days depending on event cadence; expand when necessary.
2. Prefer primary sources: issuer disclosures, MOEX disclosures, regulator notices, official filings, company results, court/regulatory records.
3. Use reputable media for context and discovery, not as a replacement for primary facts.
4. Capture publication time, event date, affected issuer/SECID, source link, and whether the item is new or a repeat.
5. Distinguish:
   - confirmed fact;
   - reported but unconfirmed claim;
   - analyst interpretation;
   - market rumor.
6. Search specifically for adverse developments and contradictory evidence, not only bullish headlines.
7. Deduplicate syndicated/repeated articles. Multiple copies of one press release are one event, not multiple confirmations.

## Phase 3: Fundamentals

Collect only metrics that can be sourced and compared:
- latest revenue, operating profit/EBITDA where meaningful, net income;
- operating and free cash flow, capex;
- net debt, liquidity, debt maturities, interest burden;
- margins and their direction;
- dividend policy, declared dividends, payout, ex-date/payment status;
- guidance and management changes;
- dilution, buybacks, capital raises, related-party/governance events;
- valuation multiples only with explicit denominator/date and comparable methodology.

Rules:
- Use the latest reported period and identify its reporting date.
- Do not mix IFRS/RAS or adjusted/unadjusted metrics without labels.
- Do not compare banks' balance-sheet ratios with industrial-company ratios as if interchangeable.
- Separate trailing data from forward guidance.
- A good company is not automatically a good purchase at any price; valuation and expectations matter.
- If a fundamental data point cannot be verified, mark it unavailable.

## Phase 4: Semantic/context layer

For each material item, extract:
- event/entity;
- what changed versus prior known state;
- novelty and recency;
- source credibility and proximity to primary evidence;
- expected direction of impact (positive/negative/mixed/unclear);
- likely horizon (intraday, weeks, quarters, structural);
- direct versus indirect exposure;
- uncertainty and counterevidence.

Semantic analysis must not become generic sentiment scoring. "Positive article tone" is not a thesis. Explain the transmission channel from event to cash flow, risk, valuation, liquidity, or market expectations.

## Phase 5: Qwen second opinion

Use Qwen only. Request review when:
- the position is material;
- evidence conflicts;
- a major event is ambiguous;
- the agent is considering a large weight change;
- the agent's thesis has a meaningful risk of confirmation bias.

Provide a compact evidence packet with facts, dates, sources, deterministic state, and the proposed thesis. Ask Qwen to:
1. identify missing information;
2. challenge causal links;
3. give strongest bear/base/bull counterarguments;
4. identify tail risks and possible narrative traps;
5. state what evidence would change its view.

Do not treat Qwen's output as verified fact. Check cited claims against primary sources. Record its view separately from the agent's own conclusion.

## Phase 6: Allocation synthesis

Only calculate target weights when the portfolio snapshot, cash, constraints, and relevant position data are available.

For each holding, report:
- current weight;
- proposed target weight;
- change in percentage points;
- action: hold / add / trim / exit / not assessable;
- deterministic state;
- fundamental/news thesis;
- strongest counterargument;
- confidence and key invalidation condition.

Portfolio-level checks:
- weights sum to 100% including cash (or explicitly explain another convention);
- no negative weights;
- position, sector, issuer, liquidity, and concentration limits are respected;
- cash is explicit;
- transaction costs, taxes, spreads, and liquidity are considered where data exists;
- changes are compared with current holdings, not an imaginary model portfolio;
- avoid churn where expected benefit is smaller than implementation friction.

If constraints are not supplied, do not invent them. Provide a provisional qualitative assessment or ask for the missing constraint rather than pretending the weights are executable.

## Phase 7: Report and journal

The report order:
1. Executive decision.
2. Portfolio and data freshness.
3. Market regime / breadth.
4. Position-by-position review.
5. Material news and fundamentals.
6. Qwen review.
7. Proposed allocation table.
8. Main risks, disconfirming evidence, and confidence.
9. Tools run / outputs still needed.
10. Journal entry.

Record both the recommendation and rejected alternatives. Preserve enough detail to compare tomorrow's decision with today's.
