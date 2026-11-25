from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "eda2" / "block_01"
DEFAULT_DOCS = ROOT / "docs" / "research" / "eda2" / "results" / "block_01"
QUANTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)
EXTREME_THRESHOLDS = (0.02, 0.05, 0.10)

STAT_COLUMNS = [
    "mean", "median", "std", "mad", "skewness", "excess_kurtosis",
    "q01", "q05", "q25", "q50", "q75", "q95", "q99",
    "left_tail_distance_1_99", "right_tail_distance_99_1",
    "right_left_tail_distance_ratio",
    "share_le_minus_2pct", "share_ge_plus_2pct", "share_abs_ge_2pct",
    "share_le_minus_5pct", "share_ge_plus_5pct", "share_abs_ge_5pct",
    "share_le_minus_10pct", "share_ge_plus_10pct", "share_abs_ge_10pct",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EDA2 Block 1: geometry of daily return distributions."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    return parser.parse_args()


def load_returns(panel_path: Path) -> tuple[pd.DataFrame, dict]:
    """Build adjacent-session log returns without bridging missing sessions."""
    if not panel_path.exists():
        raise FileNotFoundError(f"PIT panel not found: {panel_path}")

    columns = ["tradedate", "secid", "adjusted_close", "bar_available"]
    panel = pd.read_parquet(panel_path, columns=columns)
    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.upper()
    panel["adjusted_close"] = pd.to_numeric(panel["adjusted_close"], errors="coerce")
    panel["bar_available"] = pd.to_numeric(panel["bar_available"], errors="coerce")
    panel = panel.dropna(subset=["tradedate", "secid"]).sort_values(
        ["tradedate", "secid"]
    )

    if panel.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate (tradedate, secid) rows in PIT panel.")

    dates = pd.DatetimeIndex(sorted(panel["tradedate"].unique()))
    prices = panel.pivot(
        index="tradedate", columns="secid", values="adjusted_close"
    ).reindex(index=dates)
    available = panel.pivot(
        index="tradedate", columns="secid", values="bar_available"
    ).reindex(index=dates).fillna(0).eq(1)

    previous_prices = prices.shift(1)
    valid = (
        available & available.shift(1)
        & prices.gt(0) & previous_prices.gt(0)
    )
    values = np.log(
        prices.to_numpy(dtype=np.float64)
        / previous_prices.to_numpy(dtype=np.float64)
    )
    values[~valid.to_numpy()] = np.nan
    returns = pd.DataFrame(
        values, index=dates, columns=prices.columns
    ).iloc[1:].copy()

    metadata = {
        "panel_path": str(panel_path),
        "panel_rows_read": int(len(panel)),
        "panel_dates": int(len(dates)),
        "panel_tickers": int(panel["secid"].nunique()),
        "return_dates": int(len(returns)),
        "return_observations": int(np.isfinite(returns.to_numpy()).sum()),
        "return_definition": (
            "log(adjusted_close_t / adjusted_close_t-1); both observations "
            "must have bar_available=1 on adjacent panel trading sessions"
        ),
        "forward_fill": False,
        "missing_sessions_bridged": False,
        "external_data_requests": 0,
    }
    return returns, metadata


def distribution_stats(values: np.ndarray) -> dict:
    x = np.asarray(values, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = int(x.size)
    if n == 0:
        return {"n": 0}

    series = pd.Series(x)
    median = float(np.median(x))
    q = np.quantile(x, QUANTILES)
    result = {
        "n": n,
        "mean": float(np.mean(x)),
        "median": median,
        "std": float(np.std(x, ddof=1)) if n > 1 else np.nan,
        "mad": float(np.median(np.abs(x - median))),
        "skewness": float(series.skew()) if n >= 3 else np.nan,
        "excess_kurtosis": float(series.kurt()) if n >= 4 else np.nan,
        "q01": float(q[0]), "q05": float(q[1]), "q25": float(q[2]),
        "q50": float(q[3]), "q75": float(q[4]), "q95": float(q[5]),
        "q99": float(q[6]),
        "left_tail_distance_1_99": float(median - q[0]),
        "right_tail_distance_99_1": float(q[6] - median),
    }
    left = result["left_tail_distance_1_99"]
    right = result["right_tail_distance_99_1"]
    result["right_left_tail_distance_ratio"] = (
        float(right / left) if left > 0 else np.nan
    )

    for threshold in EXTREME_THRESHOLDS:
        label = f"{int(threshold * 100)}pct"
        result[f"share_le_minus_{label}"] = float(np.mean(x <= -threshold))
        result[f"share_ge_plus_{label}"] = float(np.mean(x >= threshold))
        result[f"share_abs_ge_{label}"] = float(np.mean(np.abs(x) >= threshold))
    return result


def per_security_distribution(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for secid in returns.columns:
        rows.append({"secid": secid, **distribution_stats(returns[secid].to_numpy())})
    return pd.DataFrame(rows)


def overall_summary(
    returns: pd.DataFrame, security_stats: pd.DataFrame
) -> pd.DataFrame:
    pooled = distribution_stats(returns.to_numpy().ravel())
    row = {"sample": "pooled_observations", **pooled}
    eligible = security_stats.loc[security_stats["n"] > 0]
    for column in STAT_COLUMNS:
        row[f"equal_security_avg_{column}"] = (
            float(eligible[column].mean())
            if column in eligible and eligible[column].notna().any()
            else np.nan
        )
    row["securities_with_returns"] = int(len(eligible))
    row["panel_tickers"] = int(len(returns.columns))
    return pd.DataFrame([row])


def security_heterogeneity_summary(security_stats: pd.DataFrame) -> pd.DataFrame:
    """Compact cross-security distributions, not just averages."""
    metrics = [
        "n", "mean", "median", "std", "mad", "skewness", "excess_kurtosis",
        "q01", "q05", "q95", "q99",
        "share_abs_ge_2pct", "share_abs_ge_5pct", "share_abs_ge_10pct",
    ]
    rows = []
    for metric in metrics:
        values = pd.to_numeric(security_stats[metric], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append({
            "statistic": metric,
            "n_securities": int(values.size),
            "mean_across_securities": float(values.mean()),
            "std_across_securities": float(values.std(ddof=1)) if len(values) > 1 else np.nan,
            "q10_across_securities": float(values.quantile(0.10)),
            "q25_across_securities": float(values.quantile(0.25)),
            "median_across_securities": float(values.median()),
            "q75_across_securities": float(values.quantile(0.75)),
            "q90_across_securities": float(values.quantile(0.90)),
            "min_across_securities": float(values.min()),
            "max_across_securities": float(values.max()),
        })
    return pd.DataFrame(rows)


def yearly_summary(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, sample in returns.groupby(returns.index.year):
        pooled = distribution_stats(sample.to_numpy().ravel())
        individual = pd.DataFrame([
            distribution_stats(sample[secid].to_numpy())
            for secid in sample.columns
        ])
        row = {"year": int(year), "pooled_n": pooled["n"]}
        row.update({f"pooled_{k}": v for k, v in pooled.items() if k != "n"})
        row["securities_with_returns"] = int(
            (individual["n"].fillna(0) > 0).sum()
        )
        for column in STAT_COLUMNS:
            row[f"equal_security_avg_{column}"] = (
                float(individual[column].mean())
                if column in individual and individual[column].notna().any()
                else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def daily_cross_section(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, row in returns.iterrows():
        x = row.to_numpy(dtype=np.float64)
        x = x[np.isfinite(x)]
        if x.size == 0:
            continue
        median = float(np.median(x))
        rows.append({
            "tradedate": date.date().isoformat(),
            "n_securities": int(x.size),
            "mean": float(np.mean(x)),
            "median": median,
            "std": float(np.std(x, ddof=1)) if x.size > 1 else np.nan,
            "mad": float(np.median(np.abs(x - median))),
            "iqr": float(np.quantile(x, 0.75) - np.quantile(x, 0.25)),
            "q10": float(np.quantile(x, 0.10)),
            "q25": float(np.quantile(x, 0.25)),
            "q75": float(np.quantile(x, 0.75)),
            "q90": float(np.quantile(x, 0.90)),
            "positive_share": float(np.mean(x > 0)),
            "negative_share": float(np.mean(x < 0)),
            "zero_share": float(np.mean(x == 0)),
        })
    return pd.DataFrame(rows)


def cross_section_time_summary(daily: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "n_securities", "mean", "median", "std", "mad", "iqr",
        "q10", "q25", "q75", "q90",
        "positive_share", "negative_share", "zero_share",
    ]
    rows = []
    for metric in metrics:
        x = pd.to_numeric(daily[metric], errors="coerce").dropna()
        if not x.empty:
            rows.append({
                "metric": metric,
                "n_dates": int(x.size),
                "time_mean": float(x.mean()),
                "time_median": float(x.median()),
                "time_q10": float(x.quantile(0.10)),
                "time_q90": float(x.quantile(0.90)),
            })
    return pd.DataFrame(rows)


def write_report(
    path: Path,
    returns: pd.DataFrame,
    metadata: dict,
    overall: pd.DataFrame,
    yearly: pd.DataFrame,
    cross_time: pd.DataFrame,
) -> None:
    pooled = overall.iloc[0]
    lines = [
        "# EDA2 — Блок 1. Геометрия распределения доходностей",
        "",
        "## Область анализа",
        f"- Дат доходностей: {len(returns):,}",
        f"- Бумаг в матрице: {len(returns.columns):,}",
        f"- Валидных наблюдений доходности: {metadata['return_observations']:,}",
        f"- Период: {returns.index.min().date()} — {returns.index.max().date()}",
        "- Доходность: дневная логарифмическая доходность adjusted close.",
        "- Используются только соседние сессии панели с bar_available=1 на обеих датах.",
        "- Пропущенные сессии не заполняются и не перескакиваются.",
        "",
        "## Объединённое распределение",
        f"- Среднее: {pooled['mean']:.8f}",
        f"- Медиана: {pooled['median']:.8f}",
        f"- Стандартное отклонение: {pooled['std']:.8f}",
        f"- MAD (медиана абсолютных отклонений от медианы): {pooled['mad']:.8f}",
        f"- Асимметрия: {pooled['skewness']:.6f}",
        f"- Эксцесс (Fisher): {pooled['excess_kurtosis']:.6f}",
        f"- Q01 / Q05: {pooled['q01']:.8f} / {pooled['q05']:.8f}",
        f"- Q95 / Q99: {pooled['q95']:.8f} / {pooled['q99']:.8f}",
        f"- Число бумаг с валидными доходностями: {int(pooled['securities_with_returns'])}",
        "",
        "## Равный вес бумаг",
        "Показатели усредняют индивидуальные оценки бумаг, а не отдельные наблюдения.",
        f"- Среднее индивидуальных средних: {pooled['equal_security_avg_mean']:.8f}",
        f"- Среднее индивидуальных медиан: {pooled['equal_security_avg_median']:.8f}",
        f"- Среднее индивидуальных стандартных отклонений: {pooled['equal_security_avg_std']:.8f}",
        f"- Среднее индивидуальных MAD: {pooled['equal_security_avg_mad']:.8f}",
        f"- Среднее индивидуальных эксцессов: {pooled['equal_security_avg_excess_kurtosis']:.6f}",
        "",
        "## Неоднородность между бумагами",
        "Распределения индивидуальных статистик по бумагам сохранены в security_heterogeneity_summary.csv. "
        "Таблица показывает квантили и диапазоны межбумажного разброса, а не только средние значения.",
        "",
        "## Годовая динамика",
        "Полная таблица pooled-оценок и средних индивидуальных оценок находится "
        "в yearly_distribution_summary.csv.",
        f"- Годовых срезов: {len(yearly)}",
        "",
        "## Поперечное распределение по датам",
        "Для каждой даты рассчитаны статистики поперечного сечения бумаг. "
        "Временные сводки этих рядов находятся в cross_sectional_time_summary.csv.",
        f"- Дат в сводке поперечных статистик: {int(cross_time['n_dates'].max()) if not cross_time.empty else 0}",
        "",
        "## Методологические ограничения",
        "- Pooled-оценки взвешивают каждую пару «бумага-дата» одинаково; бумаги с большим числом наблюдений имеют больший вклад.",
        "- Equal-security оценки сначала рассчитываются отдельно по каждой бумаге, затем усредняются с равным весом.",
        "- MAD не масштабирован до оценки стандартного отклонения.",
        "- Эксцесс рассчитан в определении Fisher (нормальное распределение имеет эксцесс 0).",
        "- Годовые срезы описывают изменение формы распределения, но сами по себе не доказывают структурный сдвиг.",
        "- Поперечные статистики могут зависеть от состава и размера PIT-универсума.",
        "- Нет тестов гипотез, IC, моделей, прогнозов, торговых правил или портфельных метрик.",
        "",
        "## Файлы",
        "- overall_distribution_summary.csv",
        "- security_heterogeneity_summary.csv",
        "- yearly_distribution_summary.csv",
        "- cross_sectional_time_summary.csv",
        "- EDA2_BLOCK_01_REPORT.md",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)

    returns, metadata = load_returns(args.panel)
    security_stats = per_security_distribution(returns)
    overall = overall_summary(returns, security_stats)
    security_heterogeneity = security_heterogeneity_summary(security_stats)
    yearly = yearly_summary(returns)
    daily = daily_cross_section(returns)
    cross_time = cross_section_time_summary(daily)

    security_stats.to_csv(args.output_dir / "security_distribution.csv", index=False)
    yearly.to_csv(args.output_dir / "yearly_distribution.csv", index=False)
    daily.to_csv(args.output_dir / "daily_cross_sectional_distribution.csv", index=False)

    overall.to_csv(args.docs_dir / "overall_distribution_summary.csv", index=False)
    security_heterogeneity.to_csv(
        args.docs_dir / "security_heterogeneity_summary.csv", index=False
    )
    yearly.to_csv(args.docs_dir / "yearly_distribution_summary.csv", index=False)
    cross_time.to_csv(args.docs_dir / "cross_sectional_time_summary.csv", index=False)

    metadata.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "block": 1,
        "block_name": "Геометрия распределения доходностей",
        "quantiles": list(QUANTILES),
        "extreme_absolute_return_thresholds": list(EXTREME_THRESHOLDS),
        "security_statistics_count": int(len(security_stats)),
        "security_heterogeneity_summary_rows": int(len(security_heterogeneity)),
        "yearly_slices": int(len(yearly)),
        "cross_sectional_dates": int(len(daily)),
        "method_notes": [
            "Daily log returns are computed only across adjacent panel sessions.",
            "Both endpoint observations must have bar_available=1 and positive adjusted_close.",
            "No forward-fill, imputation, or bridging over missing sessions.",
            "Pooled statistics weight each valid security-date observation equally.",
            "Equal-security statistics average per-security estimates with equal security weights.",
            "MAD is the unscaled median absolute deviation around the sample median.",
            "Excess kurtosis uses Fisher definition.",
            "Yearly and date-level summaries are descriptive, not predictive evidence.",
            "No hypothesis tests, IC, feature selection, model fitting, trading rule, or portfolio metric.",
        ],
        "machine_outputs": [
            "security_distribution.csv",
            "yearly_distribution.csv",
            "daily_cross_sectional_distribution.csv",
            "run_metadata.json",
        ],
        "research_outputs": [
            "overall_distribution_summary.csv",
            "security_heterogeneity_summary.csv",
            "yearly_distribution_summary.csv",
            "cross_sectional_time_summary.csv",
            "EDA2_BLOCK_01_REPORT.md",
        ],
    })
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(
        args.docs_dir / "EDA2_BLOCK_01_REPORT.md",
        returns, metadata, overall, yearly, cross_time,
    )

    print("EDA2 Block 1 completed.")
    print(f"Return observations: {metadata['return_observations']:,}")
    print(f"Return dates: {metadata['return_dates']:,}")
    print(f"Securities: {metadata['panel_tickers']:,}")
    print(f"Machine outputs: {args.output_dir}")
    print(f"Research outputs: {args.docs_dir}")


if __name__ == "__main__":
    main()
