# Folder: scripts/experiments/primitives/portfolios/
# File: reporting.py
# Purpose: Build metrics, assistant-facing Markdown report, and equity-curve plots.

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FOCUS_YEARS = (2024, 2025, 2026)


def max_drawdown(equity: pd.Series) -> float:
    values = pd.to_numeric(equity, errors="coerce").dropna()
    if values.empty:
        return np.nan
    return float((values / values.cummax() - 1.0).min())


def summarize_period(group: pd.DataFrame) -> dict:
    group = group.sort_values("exit_date").copy()
    returns = pd.to_numeric(group["net_return"], errors="coerce").dropna()
    if returns.empty:
        return {
            "observations": 0, "total_return": np.nan,
            "annualized_return": np.nan, "annualized_volatility": np.nan,
            "sharpe_252": np.nan, "max_drawdown": np.nan,
            "positive_share": np.nan, "average_exposure": np.nan,
            "average_turnover": np.nan, "average_missing_return_weight": np.nan,
        }

    equity = (1.0 + returns).cumprod()
    n = len(returns)
    total_return = float(equity.iloc[-1] - 1.0)
    annualized_return = (
        float(equity.iloc[-1] ** (252.0 / n) - 1.0)
        if equity.iloc[-1] > 0 and n > 0 else np.nan
    )
    daily_std = float(returns.std(ddof=1))
    return {
        "observations": n,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": daily_std * np.sqrt(252.0),
        "sharpe_252": (
            float(returns.mean() / daily_std * np.sqrt(252.0))
            if daily_std > 0 else np.nan
        ),
        "max_drawdown": max_drawdown(equity),
        "positive_share": float((returns > 0).mean()),
        "average_exposure": float(group["effective_exposure"].mean()),
        "average_turnover": float(group["turnover_one_way"].mean()),
        "average_missing_return_weight": float(
            group["missing_return_weight"].mean()
        ),
    }


def build_metrics(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    overall_rows, annual_rows = [], []
    for (strategy, cost), group in daily.groupby(
        ["strategy", "transaction_cost_bps"], sort=True
    ):
        overall_rows.append({
            "strategy": strategy, "transaction_cost_bps": cost,
            "period": "full_sample", **summarize_period(group),
        })
        for year, year_group in group.groupby(group["exit_date"].dt.year):
            annual_rows.append({
                "strategy": strategy,
                "transaction_cost_bps": cost,
                "year": int(year),
                "period_status": (
                    "partial_ytd" if int(year) == 2026 else "calendar_year"
                ),
                **summarize_period(year_group),
            })
    return pd.DataFrame(overall_rows), pd.DataFrame(annual_rows)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_Нет данных._"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame[columns].iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, (float, np.floating)):
                values.append("NA" if pd.isna(value) else f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_assistant_report(
    output_path: Path,
    daily: pd.DataFrame,
    overall: pd.DataFrame,
    annual: pd.DataFrame,
    specs: pd.DataFrame,
    breadth: pd.DataFrame,
) -> None:
    first_date = daily["signal_date"].min()
    last_date = daily["exit_date"].max()
    no_cost = overall[overall["transaction_cost_bps"].eq(0)].copy()
    focus = annual[
        annual["year"].isin(FOCUS_YEARS)
        & annual["transaction_cost_bps"].eq(0)
    ].copy()
    breadth_summary = (
        breadth.groupby("breadth_regime", dropna=False)
        .agg(
            sessions=("tradedate", "size"),
            mean_level=("breadth_level", "mean"),
            mean_change_5=("breadth_change_5", "mean"),
        )
        .reset_index()
    )
    breadth_summary["mean_level"] /= 100.0
    breadth_summary["mean_change_5"] /= 100.0

    lines = [
        "# Primitive portfolio application experiment",
        "",
        "## Purpose",
        "",
        "Application-mapping experiment, not strategy optimization. It compares simple portfolio uses of the three selected primitives and tests market breadth as an exposure scaler.",
        "",
        "## Data and execution",
        "",
        f"- Signal dates: {first_date:%Y-%m-%d} to {last_date:%Y-%m-%d}.",
        "- Universe: PIT TOP50; only signal-date rows with an actual bar.",
        "- Baseline: 2% per available PIT TOP50 constituent.",
        "- Primitive portfolios: TOP10/BOTTOM10, 10% per selected constituent.",
        "- Signal after close T; entry OPEN T+1; exit/rebalance OPEN T+2.",
        "- Daily returns are sequential open-to-open holding intervals, not overlapping H5/H10/H20 forecasts.",
        "- If either required forward OPEN is missing, the affected target weight is treated as cash for that interval and reported.",
        "- Breadth level: share of PIT TOP50 with price_sma20 > 0.",
        "- Breadth change: five-session change in breadth level, percentage points.",
        "- Sizing: >50% and rising = 100%; >50% and flat/falling = 75%; <=50% and rising = 50%; <=50% and flat/falling = 25%.",
        "- Flat breadth change is assigned to flat/falling.",
        "- Costs: one-way turnover multiplied by 0, 10, or 25 bps.",
        "- SQLite and feature inputs are read-only.",
        "",
        "## Interpretation warnings",
        "",
        "- Simplified daily-rebalanced portfolio proxy, not a production execution simulator.",
        "- Open-to-open returns exclude market impact, liquidity constraints, lot sizes, taxes, and intraday execution details.",
        "- Baseline and TOP10 portfolios differ in concentration by design.",
        "- 2026 is partial YTD through the final available data date; do not compare it with full years as an equal-length period.",
        "- Results do not establish standalone alpha or authorize production trading rules.",
        "",
        "## Breadth regime coverage",
        "",
        markdown_table(
            breadth_summary,
            ["breadth_regime", "sessions", "mean_level", "mean_change_5"],
        ),
        "",
        "## Full-sample metrics, zero transaction costs",
        "",
        markdown_table(
            no_cost.sort_values("strategy"),
            [
                "strategy", "observations", "total_return",
                "annualized_volatility", "sharpe_252", "max_drawdown",
                "positive_share", "average_exposure", "average_turnover",
            ],
        ),
        "",
        "## Focus years: 2024, 2025, 2026 (zero transaction costs)",
        "",
        markdown_table(
            focus.sort_values(["year", "strategy"]),
            [
                "year", "period_status", "strategy", "observations",
                "total_return", "annualized_volatility", "max_drawdown",
                "positive_share", "average_exposure",
            ],
        ),
        "",
        "## All annual metrics and cost scenarios",
        "",
        markdown_table(
            annual.sort_values(["year", "strategy", "transaction_cost_bps"]),
            [
                "year", "strategy", "transaction_cost_bps",
                "observations", "total_return", "max_drawdown",
                "average_exposure", "average_turnover",
            ],
        ),
        "",
        "## Strategy definitions",
        "",
        markdown_table(
            specs,
            [
                "strategy", "base_strategy", "uses_breadth",
                "feature", "top_n", "base_weight", "breadth_sizing",
            ],
        ),
        "",
        "## Outputs",
        "",
        "- daily_equity_curves.csv: daily gross/net returns, equity, exposure, turnover, missing-return weight.",
        "- full_sample_metrics.csv: full-sample metrics by strategy and cost.",
        "- annual_metrics.csv: calendar-year metrics, including separate 2024/2025/2026 rows.",
        "- strategy_specs.csv: exact strategy definitions.",
        "- breadth_daily.csv: daily breadth level, five-session change, and regime.",
        "- figures/: full-sample and focus-year equity curves.",
        "",
        "## Questions for scanner documentation",
        "",
        "1. Which primitive directions produce meaningfully different portfolio behaviour?",
        "2. Does breadth scaling reduce downside exposure in 2024-2026, or mostly suppress participation?",
        "3. Does breadth add value beyond the same portfolio without breadth scaling?",
        "4. Are differences robust to turnover costs and constituent churn?",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def plot_curves(daily: pd.DataFrame, output_dir: Path) -> None:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    plot_data = daily.sort_values("exit_date").copy()

    def draw(frame: pd.DataFrame, title: str, filename: str) -> None:
        if frame.empty:
            return
        fig, ax = plt.subplots(figsize=(16, 9))
        for (strategy, cost), group in frame.groupby(
            ["strategy", "transaction_cost_bps"], sort=True
        ):
            # The plots show 0 bps curves for readability.
            # Cost sensitivity is preserved in CSV and Markdown.
            if cost != 0:
                continue
            group = group.sort_values("exit_date")
            equity = (1.0 + group["net_return"]).cumprod()
            ax.plot(
                group["exit_date"], equity, linewidth=1.25, label=strategy
            )
        ax.set_title(title)
        ax.set_ylabel("Equity (initial = 1.0)")
        ax.set_xlabel("Date")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8)
        fig.tight_layout()
        fig.savefig(figure_dir / filename, dpi=160, bbox_inches="tight")
        plt.close(fig)

    draw(
        plot_data,
        "Primitive portfolios: full sample (0 bps)",
        "equity_full_sample.png",
    )
    for year in FOCUS_YEARS:
        subset = plot_data[plot_data["exit_date"].dt.year.eq(year)].copy()
        if not subset.empty:
            draw(
                subset,
                f"Primitive portfolios: {year} "
                f"({'partial YTD' if year == 2026 else 'calendar year'})",
                f"equity_{year}.png",
            )
