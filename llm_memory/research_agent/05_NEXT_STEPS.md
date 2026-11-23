# Next Steps and Open Risks

Last updated: 2026-11-23

## Current research state

The first primitive research cycle and the hypothesis of building a market-state screener from selected primitives are closed.

Current runtime information layer:
- Instrument state: `drawdown_60`, `zscore_sma20_20`, `realized_vol_60`.
- Separate market-state context: `breadth_change_5` (primary) and `breadth_sma20` (reference).
- Screener: `scripts/tools/01_primitive_screener.py`.
- Downstream specification: `docs/tools/01_primitive_screener.md`.

The screener is descriptive only. It does not generate trades, portfolio weights, or allocation instructions. The user's 100/75/50/25% breadth exposure schedule remains a separate heuristic, not an approved statistically validated allocation model.

## Next research cycle: analytical capability and gap assessment

The next task is **not** to mine another primitive family by default. First establish what the completed screener and current data environment have made possible, then identify the most consequential capability gaps.

The assessment should answer:

1. **What can the system now know?**
   - What can be calculated directly from the internal historical market dataset?
   - What does the screener reveal at runtime, at instrument and market level?
   - Which questions can be answered historically and reproducibly?
   - Which outputs are descriptive, statistically validated, or merely illustrative?

2. **What can the system not know reliably yet?**
   - Which market questions are blocked by missing variables, insufficient history, poor coverage, or absent data sources?
   - Which questions require external context or semantic interpretation?
   - Which answers are currently dependent on one-off web retrieval rather than a repeatable data/tool interface?
   - Where are temporal provenance, source reliability, entity mapping, or update frequency weak?

3. **Which capabilities should be built next?**
   - Identify concrete candidate tools, data interfaces, methods, or research subsystems.
   - For each, state the capability gap, required inputs, expected output, validation design, dependencies, and likely failure modes.
   - Distinguish foundational infrastructure from an analytical tool that depends on it.
   - Prioritize by expected expansion of reliable analytical capability, not by novelty or apparent sophistication.

4. **What should the next experiment establish?**
   - Select one bounded research question that closes a demonstrated gap.
   - Define a test that can reject the idea, not merely produce an interesting chart.
   - Do not begin implementation until the research question, data requirements, and validation logic are clear.

## Data reality and constraints

- The repository contains an internal historical market-data pipeline. Its exact coverage and limitations are recorded in `02_DATASET_PIPELINE.md`.
- There is **no internal fundamental-data dataset or fundamental-data pipeline**.
- News, company context, market semantics, and fundamental information are retrieved from the internet/external sources in the agent workflow.
- Current web retrieval is not equivalent to a persistent, timestamped historical dataset. Do not use present-day information to support historical point-in-time claims.
- Any future external-data tool must consider source quality, retrieval/publication timestamps, entity resolution, temporal availability, update cadence, reproducibility, and failure handling.
- Do not assume that a new data source is useful merely because it is accessible. Establish coverage and reliability.

## Explicitly retired proposal

The previous proposal to make conditional downside-risk analysis across breadth regimes the immediate next research project is **not the current plan**. It was a premature continuation of the previous breadth topic and did not follow from a full assessment of the system's capability gaps. Do not treat it as approved or automatically resume it.

## Dataset and operational risks

- Verify the refresh script locally before relying on it.
- Resolve delayed publication after an empty MOEX response, calendar-yesterday cutoff, and missing SECID/board-pair onboarding.
- Do not rebuild completed historical-universe/raw/audit/adjustment stages without a concrete defect.
- Keep raw observations immutable and derived datasets rebuildable.
- Do not claim local execution or validation from GitHub code inspection alone.

## Research discipline

- No broad feature fishing.
- Do not restrict future research to price-derived primitives or breadth.
- Do not assume internal fundamental data exists.
- Do not optimize analytical tools for CAGR, Sharpe, MDD, or portfolio return as universal truth criteria.
- Distinguish information validation from a portfolio application experiment.
- The Research Agent recommends; the user approves scope changes and production promotion.
