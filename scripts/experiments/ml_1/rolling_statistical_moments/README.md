

## Research Audit 01: HAC status (2026-11-25)

The original first-pass HAC inference is invalid for dates omitted by the minimum cross-section filter: the old implementation drops missing daily IC rows and then treats the remaining observations as equally spaced.

The repository already builds a complete TQBR/EQBR trading-session calendar in `run_experiment.py::load_adjusted_history()`. The current `evaluation.py` does not pass this calendar into the HAC layer. See `llm_memory/research_agent/06_ML_DIRECTION_FEATURE_RESEARCH.md` for the detailed audit log and current next steps.

A provisional calendar-aware HAC implementation has passed six local unit tests and Monte-carlo checks for IID and stationary AR(1) processes with MCAR missingness. This is not yet production validation. In particular, formal missing-data HAC literature distinguishes Amplitude Modulated and Equal Spacing estimators; compare both and validate the exact formula before using real-data p-values.

No updated IC inference or portfolio metrics have been generated as part of this audit.
