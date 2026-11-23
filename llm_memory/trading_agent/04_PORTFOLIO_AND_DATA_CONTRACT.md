# Portfolio and Data Contract

Last updated: 2026-11-23

## Why this file exists

The Trading Agent cannot produce defensible target weights without a point-in-time description of the portfolio and its constraints. The existence of a portfolio is not equivalent to the agent having access to it.

## Minimum portfolio snapshot

One row per position, plus an explicit cash row or cash summary.

Required fields:
- `snapshot_at`: timestamp with timezone;
- `account_id` or a non-sensitive account label;
- `secid` / ticker / instrument identifier;
- `quantity`;
- `market_value`;
- `currency`;
- `portfolio_weight` or enough data to calculate it consistently;
- `cash_balance` and cash currency;
- `price_asof` / valuation timestamp.

Strongly recommended:
- average cost / cost basis;
- accrued coupon and nominal for bonds, if bonds are in scope;
- instrument type and board;
- blocked/unavailable quantity;
- pending orders and unsettled cash;
- issuer/sector mapping;
- tax/commission assumptions if relevant.

Do not store account passwords, API keys, tokens, or unnecessary personal identifiers in repository memory.

## Portfolio constraints to establish

- permitted universe and excluded instruments;
- maximum single-position and issuer weights;
- sector / industry concentration limits;
- minimum cash or liquidity reserve;
- maximum daily turnover / number of trades;
- whether short positions, leverage, derivatives, bonds, funds, and foreign securities are allowed;
- whether additions are allowed or the agent may only manage existing positions;
- tax and transaction-cost treatment;
- intended investment horizon and risk budget;
- whether the existing model portfolio is a hard baseline or only an input.

Unknown constraints remain unknown. The agent must not fill them with convenient assumptions.

## Instrument identity and coverage

- MOEX SECID is the instrument identifier for the deterministic share dataset.
- Do not merge different SECIDs by issuer, ISIN, ticker similarity, or company name without an explicit mapping rule.
- The current deterministic screener covers the latest PIT TOP50 panel, not every listed instrument or every possible portfolio holding.
- A portfolio holding outside the current PIT TOP50 must be marked out-of-universe for screener purposes, not assigned a fabricated primitive state.
- Bonds, ETFs, preferred shares, and other instruments may need different data pipelines and fundamental schemas. Do not pass them through common-share metrics blindly.

## Timestamp and freshness contract

Every input must have:
- observation/effective timestamp;
- publication timestamp where relevant;
- retrieval timestamp;
- source;
- coverage and missingness status.

Market data uses the latest completed MOEX session, not an assumed current-day close. Fundamental data uses its reporting period and publication time. News uses event time and publication time separately.

## Missing-data behavior

- Missing is not zero.
- Stale is not current.
- Unverified is not confirmed.
- Conflicting sources are recorded, not silently averaged.
- If a critical position lacks price, identity, or weight, do not produce precise target weights for it.
- If a portfolio export is partial, state which positions are missing and how that limits the total allocation.
