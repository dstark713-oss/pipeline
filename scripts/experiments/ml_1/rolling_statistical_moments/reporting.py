# Folder: scripts/experiments/ml_1/rolling_statistical_moments/
# File: reporting.py
# Purpose: Persist experiment outputs and a concise Markdown report.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def write_report(
    output_dir: Path,
    observations: pd.DataFrame,
    daily_ic: pd.DataFrame,
    summary: pd.DataFrame,
    coverage: pd.DataFrame,
    redundancy: pd.DataFrame,
    metadata: dict,
) -> None:
    lines = [
        "# Rolling Statistical Moments: Research Report",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Signal rows: {len(observations):,}",
        f"- Dates: {observations['tradedate'].nunique():,}",
        f"- Securities: {observations['secid'].nunique():,}",
        f"- Features: {len(metadata['feature_columns'])}",
        f"- Target: binary adjusted Close direction, t to t+{metadata['horizon']}",
        "",
        "## Methodology",
        "",
        "- Signal-date universe: historical PIT TOP50 membership with bar_available = 1.",
        "- Feature history: adjusted daily bars for each SECID, reindexed to the TQBR/EQBR market calendar.",
        "- Input: one-session log returns from adjusted Close.",
        "- Rolling windows: 20, 60, 120, 240 sessions; full windows only.",
        "- No forward-fill; missing closes are not bridged.",
        "- Pearson IC is point-biserial correlation because the target is binary.",
        "- Rank IC is Spearman correlation; binary-target ties are present.",
        "- Daily cross-sections with fewer than the configured minimum N are omitted.",
        "- HAC/Newey-West lag is 4; this is a first-pass correction for overlapping labels, not a guarantee of valid inference.",
        "- Benjamini-Hochberg correction is applied separately to IC and Rank IC p-values.",
        "- No portfolio metrics or strategy backtest are calculated.",
        "",
        "## IC summary",
        "",
        summary.to_string(index=False, float_format=lambda x: f"{x:.5f}"),
        "",
        "## Feature coverage",
        "",
        coverage.to_string(index=False, float_format=lambda x: f"{x:.3f}"),
        "",
        "## Highest median absolute cross-sectional correlations",
        "",
        redundancy.head(30).to_string(index=False, float_format=lambda x: f"{x:.5f}"),
        "",
        "## Interpretation warnings",
        "",
        "- IC is an association diagnostic, not evidence of causality or standalone economic value.",
        "- A weak standalone IC does not rule out conditional or interaction information.",
        "- Correlation is a redundancy diagnostic, not a complete test of information independence.",
        "- Larger windows may stabilize estimates but can mix market regimes and respond more slowly.",
        "- Review coverage, period stability, IC dispersion, and feature redundancy before selecting any feature.",
        "- These results are exploratory and must not be used as portfolio-performance evidence.",
        "",
    ]

    report_path = output_dir / "research_report.md"
    temporary = report_path.with_name(report_path.name + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(report_path)
