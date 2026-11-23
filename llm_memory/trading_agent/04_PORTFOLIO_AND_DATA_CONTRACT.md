# Portfolio and Data Contract

Last updated: 2026-11-23

## Purpose

Keep a simple, reliable record of the current allocation. This is not a brokerage integration specification and does not require a complex portfolio reader.

## Current known baseline

User-reported on 2026-11-23:
- T: 10%
- GCHE: 2%

The remaining 88% is unclassified. Do not assume it is cash, other securities, or available buying power until the user clarifies or supplies a complete allocation snapshot.

## Update rules

- Treat the latest user-provided allocation/snapshot and explicitly agreed allocation decisions as the source of truth.
- Record the effective date/time of each update.
- Preserve prior snapshots in the journal so decisions can be evaluated later.
- Do not silently overwrite a prior allocation with an inferred one.
- Ask for a full snapshot only when the decision requires it; otherwise work with known positions and clearly state the limitation.
- Never infer quantities, market values, cash, cost basis, or account constraints from weights alone.

## Daily market snapshot

The user supplies local market/screener outputs. The agent requests what is needed for the current decision, checks dates/coverage, and records missing or stale inputs. Do not claim access to local files or local execution.

## Privacy

Do not request or store brokerage passwords, API keys, tokens, or unnecessary personal/account identifiers.