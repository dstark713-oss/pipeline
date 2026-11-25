# Portfolio and Data Contract

Last updated: 2026-11-24

## Purpose

Keep a simple, reliable record of the current allocation. This is not a brokerage integration specification and does not require a complex portfolio reader.

## Current known baseline

User-reported on 2026-11-23:
- T: 10%
- GCHE: 2%
- LQDT: 88%

Total: 100%. LQDT is a money-market fund, not idle cash. User's current yield estimate is approximately 12% annualized, based on the current key-rate/fund-expense environment; it is floating and not guaranteed.

## Portfolio-model constraints supplied by the user

- Maximum 10 simultaneous equity names.
- Aggregate signed portfolio loading between -0.5 and +1.5.
- No individual-security weight cap supplied.
- No separate gross-exposure cap supplied.
- Do not invent either missing limit.
- Short positions and leverage are permitted by the stated aggregate range, but not automatically recommended.

The 3%, 6%, 9%, and 12% equity exposures belong to the historical breadth test only. They are derived by applying 25%, 50%, 75%, and 100% multipliers to the 12% baseline equity sleeve. They are not per-security limits.

## Historical cash benchmark contract

- Fixed 8% annual effective rate for the full historical breadth-test period.
- User-provided derivation: RGBITR minus RGBI.
- This is a historical cash proxy assumption, not actual LQDT historical performance.
- Do not add LQDT or RGBI data to the dataset solely for this test.
- Do not use the current ~12% LQDT yield as the historical cash rate.
- No sensitivity analysis for the current run.

## Update rules

- Treat the latest user-provided allocation/snapshot and explicitly agreed allocation decisions as the source of truth.
- Record the effective date/time of each update.
- Preserve prior snapshots in the journal so decisions can be evaluated later.
- Do not silently overwrite a prior allocation with an inferred one.
- Ask for a full snapshot only when the decision requires it; otherwise work with known positions and clearly state the limitation.
- Never infer quantities, market values, cost basis, or account constraints from weights alone.

## Daily market snapshot

The user supplies local market/screener outputs. The agent requests what is needed for the current decision, checks dates/coverage, and records missing or stale inputs. Do not claim access to local files or local execution.

## Privacy

Do not request or store brokerage passwords, API keys, tokens, or unnecessary personal/account identifiers.

## LQDT data-source contract

- LQDT is NOT included in `data/processed/top50/top50_panel.parquet` or the approved adjusted SQLite universe (`TQBR`/`EQBR`).
- Whenever LQDT is required as an opportunity-cost benchmark, fetch its own daily price history separately from MOEX ISS. Do not silently substitute the key rate, a fixed historical cash proxy, or an unrelated series.
- Use the MOEX ISS daily candles endpoint for LQDT, discover/confirm its active board (expected fund board `TQTF`), paginate with `start`, and preserve source, board, date range, retrieval timestamp, and raw close values.
- Align LQDT returns with asset/index returns by exact trading date. Do not forward-fill missing sessions. Report unmatched dates and coverage.
- For forward H1/H5/H20 comparisons, calculate synchronized compounded returns over the same future trading sessions. Distinguish current LQDT yield from historical realized LQDT returns.
- If MOEX ISS retrieval fails or coverage is insufficient, mark the benchmark `NOT ASSESSABLE`; do not proceed as if LQDT were absent by design.
