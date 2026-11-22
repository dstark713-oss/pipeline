# Dataset pipeline roadmap

## Stage 1: historical universe

- Query MOEX ISS listing catalog across historical range.
- Cache raw API pages locally.
- Fetch and cache security metadata.
- Classify securities; unknown or failed metadata is quarantined, not silently accepted.
- Preserve listing board history and source metadata.

## Stage 2: raw daily history

- Build download jobs by security, board and calendar-year chunk.
- Persist raw observations into local SQLite.
- Use retry/backoff and checkpoint commits.
- Resume incomplete jobs after interruption.
- Keep raw observations unmodified; retain distinct board observations.
- Track failures and collection summaries.

## Stage 3: validation

- Coverage and date-range checks.
- Duplicate and OHLCV anomaly audits.
- Missing-history investigation.
- Maintain a persistent anomaly register.

## Stage 4: processing

Transformations and adjusted data are implemented separately from the raw collector and must be reproducible.

## Stage 5: panel

Build the research panel only after raw collection and processing policies are documented and audited.