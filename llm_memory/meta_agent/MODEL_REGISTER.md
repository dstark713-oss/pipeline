# Model Register and Evidence Policy

Last updated: 2026-11-27

This file is the canonical index for model identity, versions, validation evidence and conditional preference. It is not a leaderboard and does not assign arbitrary trust scores.

## Status vocabulary

- **RESEARCH** — under development; not eligible to supply live portfolio signals.
- **VALIDATION** — frozen candidate undergoing predeclared validation.
- **SHADOW** — producing time-stamped predictions without controlling real capital.
- **ELIGIBLE** — validation reviewed; may be considered for portfolio use after explicit user approval.
- **ACTIVE** — explicitly approved current signal source for a defined use case.
- **SUSPENDED** — temporarily not eligible because of data, drift, operational or performance concerns.
- **RETIRED** — no longer used; retain history.

## Required record per model/version

| Field | Required information |
|---|---|
| Identity | Model ID, name, family, version, code/repository revision, owner |
| Purpose | Research question, target, horizon, universe, intended use |
| Data | Dataset/version, point-in-time rules, feature snapshot, as-of time |
| Design | Training and validation windows, WF protocol, retraining cadence |
| Coverage | Eligible observations, prediction coverage, missingness, sample size |
| Predictive evidence | Task-appropriate metrics, calibration, uncertainty, baseline comparison |
| Robustness | Subperiod/regime stability, sensitivity, leakage checks, failure modes |
| Economic evidence | Only under an approved protocol: costs, turnover, capacity and net outcomes |
| Operational evidence | Runtime reliability, input drift, latency, missing inputs |
| Deployment evidence | Shadow/paper observations and actual live outcomes, stored separately |
| Governance | Status, approval, limitations, review date and reason for changes |

## Preference policy

1. Compare models on common samples and protocols where possible.
2. Do not compare unlike targets, horizons or universes as if they were interchangeable.
3. Keep predictive quality, calibration, economic value, robustness and operational reliability separate.
4. Show sample size and uncertainty beside every metric.
5. Prefer a model only for a defined task/use case where evidence is stronger.
6. Preserve model disagreement; do not average predictions or vote by default.
7. A single high backtest metric, short strong period or in-sample result is insufficient.
8. No fixed weighted score or scalar trust rating until enough comparable evidence exists and the user approves the methodology.

## Current registry

No production-eligible model is recorded in this file as of 2026-11-27. Populate entries only from reproducible research artifacts and verified prediction logs. Never infer a model's performance from a conversation summary alone.
