from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "eda2" / "block_04"
DEFAULT_DOCS = ROOT / "docs" / "research" / "eda2" / "results" / "block_04"

PERIODS = (
    ("2005_2012", "2005-01-01", "2012-12-31"),
    ("2013_2019", "2013-01-01", "2019-12-31"),
    ("2020_2026", "2020-01-01", "2026-12-31"),
)
ROLLING_WINDOWS = (60, 120, 240)
ACF_LAGS = (1, 5, 10, 20)
MIN_ACF_PAIRS = 60

CROSS_METRICS = (
    "mean", "median", "std", "mad", "iqr",
    "q05", "q25", "q50", "q75", "q95",
    "positive_share", "negative_share", "zero_share", "n_securities",
)
TIME_SERIES_METRICS = (
    "std", "mad", "iqr", "positive_share", "negative_share", "n_securities",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EDA2 Block 4: cross-sectional dispersion and breadth summaries."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    return parser.parse_args()


def load_returns(panel_path: Path) -> tuple[pd.DataFrame, dict]:
    """Build adjacent-panel-session log returns; do not fill or bridge gaps."""
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

    previous = prices.shift(1)
    valid = available & available.shift(1) & prices.gt(0) & previous.gt(0)
    values = np.log(
        prices.to_numpy(dtype=np.float64) / previous.to_numpy(dtype=np.float64)
    )
    values[~valid.to_numpy()] = np.nan
    returns = pd.DataFrame(values, index=dates, columns=prices.columns).iloc[1:].copy()

    metadata = {
        "panel_path": str(panel_path),
        "panel_rows_read": int(len(panel)),
        "panel_dates": int(len(dates)),
        "panel_tickers": int(panel["secid"].nunique()),
        "return_dates": int(len(returns)),
        "return_observations": int(np.isfinite(returns.to_numpy()).sum()),
        "return_definition": (
            "log(adjusted_close_t / adjusted_close_t-1); both endpoint rows "
            "must have bar_available=1 on adjacent panel trading sessions"
        ),
        "forward_fill": False,
        "missing_sessions_bridged": False,
        "external_data_requests": 0,
    }
    return returns, metadata


def daily_cross_section(returns: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for date, row in returns.iterrows():
        x = row.to_numpy(dtype=np.float64)
        x = x[np.isfinite(x)]
        if x.size == 0:
            continue
        median = float(np.median(x))
        q05, q25, q50, q75, q95 = np.quantile(x, [0.05, 0.25, 0.50, 0.75, 0.95])
        rows.append({
            "tradedate": date,
            "n_securities": int(x.size),
            "mean": float(np.mean(x)),
            "median": median,
            "std": float(np.std(x, ddof=1)) if x.size > 1 else np.nan,
            "mad": float(np.median(np.abs(x - median))),
            "iqr": float(q75 - q25),
            "q05": float(q05),
            "q25": float(q25),
            "q50": float(q50),
            "q75": float(q75),
            "q95": float(q95),
            "positive_share": float(np.mean(x > 0)),
            "negative_share": float(np.mean(x < 0)),
            "zero_share": float(np.mean(x == 0)),
        })
    if not rows:
        return pd.DataFrame(columns=["tradedate", *CROSS_METRICS])
    return pd.DataFrame(rows).sort_values("tradedate").reset_index(drop=True)


def summarize_series(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {"n_dates": 0}
    return {
        "n_dates": int(x.size),
        "mean": float(x.mean()),
        "median": float(x.median()),
        "std": float(x.std(ddof=1)) if x.size > 1 else np.nan,
        "q10": float(x.quantile(0.10)),
        "q25": float(x.quantile(0.25)),
        "q75": float(x.quantile(0.75)),
        "q90": float(x.quantile(0.90)),
        "min": float(x.min()),
        "max": float(x.max()),
    }


def temporal_distribution_summary(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in CROSS_METRICS:
        rows.append({"metric": metric, **summarize_series(daily[metric])})
    return pd.DataFrame(rows)


def yearly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dates = pd.to_datetime(daily["tradedate"])
    for year, indices in dates.groupby(dates.dt.year).groups.items():
        sample = daily.loc[indices]
        for metric in CROSS_METRICS:
            rows.append({
                "year": int(year),
                "metric": metric,
                **summarize_series(sample[metric]),
            })
    return pd.DataFrame(rows)


def rolling_summary(daily: pd.DataFrame) -> pd.DataFrame:
    indexed = daily.set_index(pd.to_datetime(daily["tradedate"]))
    rows = []
    for metric in CROSS_METRICS:
        series = pd.to_numeric(indexed[metric], errors="coerce")
        for window in ROLLING_WINDOWS:
            rolling_mean = series.rolling(window=window, min_periods=window).mean()
            rolling_std = series.rolling(window=window, min_periods=window).std(ddof=1)
            mean_summary = summarize_series(rolling_mean)
            std_summary = summarize_series(rolling_std)
            rows.append({
                "metric": metric,
                "window_sessions": window,
                "n_rolling_windows": mean_summary["n_dates"],
                "rolling_mean_median": mean_summary.get("median", np.nan),
                "rolling_mean_q10": mean_summary.get("q10", np.nan),
                "rolling_mean_q90": mean_summary.get("q90", np.nan),
                "rolling_std_median": std_summary.get("median", np.nan),
                "rolling_std_q10": std_summary.get("q10", np.nan),
                "rolling_std_q90": std_summary.get("q90", np.nan),
            })
    return pd.DataFrame(rows)


def pairwise_lag_acf(values: np.ndarray, lag: int) -> tuple[float, int]:
    """Global-centred ACF using only valid pairs exactly lag rows apart."""
    x = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(x)
    n_valid = int(finite.sum())
    if n_valid < MIN_ACF_PAIRS or len(x) <= lag:
        return np.nan, 0
    mean = float(np.mean(x[finite]))
    denominator = float(np.sum(np.square(x[finite] - mean)))
    if denominator <= 0:
        return np.nan, 0
    left, right = x[:-lag], x[lag:]
    pair_valid = np.isfinite(left) & np.isfinite(right)
    n_pairs = int(pair_valid.sum())
    if n_pairs < MIN_ACF_PAIRS:
        return np.nan, n_pairs
    numerator = float(np.sum((left[pair_valid] - mean) * (right[pair_valid] - mean)))
    return numerator / denominator, n_pairs


def acf_summary(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in TIME_SERIES_METRICS:
        values = daily[metric].to_numpy(dtype=np.float64)
        for lag in ACF_LAGS:
            acf, n_pairs = pairwise_lag_acf(values, lag)
            rows.append({
                "metric": metric,
                "lag": lag,
                "acf": acf,
                "valid_lag_pairs": n_pairs,
                "valid_observations": int(np.isfinite(values).sum()),
            })
    return pd.DataFrame(rows)


def period_summary(daily: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(daily["tradedate"])
    rows = []
    for name, start, end in PERIODS:
        sample = daily.loc[(dates >= start) & (dates <= end)]
        for metric in CROSS_METRICS:
            rows.append({
                "period": name,
                "metric": metric,
                **summarize_series(sample[metric]) if not sample.empty
                else {"n_dates": 0},
            })
    return pd.DataFrame(rows)


def write_report(
    path: Path,
    daily: pd.DataFrame,
    metadata: dict,
    time_summary: pd.DataFrame,
    acf: pd.DataFrame,
    rolling: pd.DataFrame,
) -> None:
    lookup = time_summary.set_index("metric")
    lines = [
        "# EDA2 — Блок 4. Поперечный разброс и breadth-статистики",
        "",
        "## Область анализа",
        f"- Дат панели: {metadata['panel_dates']:,}",
        f"- Дат с валидным поперечным сечением: {len(daily):,}",
        f"- Бумаг в панели: {metadata['panel_tickers']:,}",
        f"- Валидных наблюдений доходности: {metadata['return_observations']:,}",
        f"- Период: {pd.to_datetime(daily['tradedate']).min().date()} — "
        f"{pd.to_datetime(daily['tradedate']).max().date()}",
        "- Единица анализа: поперечное сечение бумаг в одну дату.",
        "",
        "## Временные распределения поперечных метрик",
        "",
        "| Метрика | Дат | Среднее | Медиана | Q10 | Q90 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for metric in CROSS_METRICS:
        row = lookup.loc[metric]
        lines.append(
            f"| {metric} | {int(row['n_dates'])} | {row['mean']:.6g} | "
            f"{row['median']:.6g} | {row['q10']:.6g} | {row['q90']:.6g} |"
        )
    lines.extend([
        "",
        "## Временная зависимость агрегированных рядов",
        "ACF рассчитана для последовательных строк панели: пропуски не заполняются, "
        "а пары через отсутствующие значения не соединяются. Для каждой оценки требуется "
        f"не менее {MIN_ACF_PAIRS} валидных лаговых пар.",
        "",
        "| Метрика | Лаг | ACF | Валидных пар |",
        "|---|---:|---:|---:|",
    ])
    for row in acf.itertuples(index=False):
        value = f"{row.acf:.5f}" if pd.notna(row.acf) else "NA"
        lines.append(f"| {row.metric} | {row.lag} | {value} | {row.valid_lag_pairs} |")
    lines.extend([
        "",
        "## Скользящие сводки",
        "Для окон 60, 120 и 240 сессий рассчитаны rolling mean и rolling standard deviation "
        "каждого поперечного ряда. Здесь приведены медианы и Q10/Q90 распределений этих "
        "скользящих оценок; полная таблица находится в rolling_summary.csv.",
        "",
        "| Метрика | Окно | Число окон | Медиана rolling mean | Медиана rolling std |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in rolling.itertuples(index=False):
        mean_value = f"{row.rolling_mean_median:.6g}" if pd.notna(row.rolling_mean_median) else "NA"
        std_value = f"{row.rolling_std_median:.6g}" if pd.notna(row.rolling_std_median) else "NA"
        lines.append(
            f"| {row.metric} | {row.window_sessions} | {row.n_rolling_windows} | "
            f"{mean_value} | {std_value} |"
        )
    lines.extend([
        "",
        "## Методологические ограничения",
        "- Доходности рассчитываются между соседними датами панели при bar_available=1 и положительных adjusted_close на обеих конечных точках.",
        "- Поперечные метрики используют только валидные доходности соответствующей даты; N сохраняет размер фактического сечения.",
        "- MAD — немасштабированная медиана абсолютных отклонений от медианы.",
        "- ACF использует глобальное среднее и дисперсию валидного ряда; числитель включает только валидные пары, разделённые ровно заданным числом строк панели.",
        "- Скользящие окна измеряются в строках дат панели и требуют полного окна; значения не интерполируются.",
        "- Период 2020–2026 включает неполный 2026 год. Периодные сравнения описательные и не являются тестом структурного сдвига.",
        "- Breadth здесь означает доли положительных/отрицательных/нулевых доходностей, а не торговые сигналы.",
        "- Нет моделей, прогнозов, IC, отбора признаков, торговых правил или портфельных метрик.",
        "",
        "## Файлы",
        "- daily_cross_sectional_metrics.csv (машинный)",
        "- run_metadata.json (машинный)",
        "- temporal_distribution_summary.csv",
        "- yearly_summary.csv",
        "- period_summary.csv",
        "- rolling_summary.csv",
        "- aggregate_acf_summary.csv",
        "- EDA2_BLOCK_04_REPORT.md",
        "",
        "Числа формируются только после фактического локального запуска скрипта.",
    ])
    path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)

    returns, metadata = load_returns(args.panel)
    daily = daily_cross_section(returns)
    time_summary = temporal_distribution_summary(daily)
    yearly = yearly_summary(daily)
    periods = period_summary(daily)
    rolling = rolling_summary(daily)
    acf = acf_summary(daily)

    daily_machine = daily.copy()
    daily_machine["tradedate"] = pd.to_datetime(daily_machine["tradedate"]).dt.strftime("%Y-%m-%d")
    daily_machine.to_csv(args.output_dir / "daily_cross_sectional_metrics.csv", index=False)
    time_summary.to_csv(args.docs_dir / "temporal_distribution_summary.csv", index=False)
    yearly.to_csv(args.docs_dir / "yearly_summary.csv", index=False)
    periods.to_csv(args.docs_dir / "period_summary.csv", index=False)
    rolling.to_csv(args.docs_dir / "rolling_summary.csv", index=False)
    acf.to_csv(args.docs_dir / "aggregate_acf_summary.csv", index=False)

    metadata.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "block": 4,
        "block_name": "Поперечный разброс и breadth-статистики",
        "cross_sectional_metrics": list(CROSS_METRICS),
        "time_series_metrics_for_acf": list(TIME_SERIES_METRICS),
        "acf_lags": list(ACF_LAGS),
        "min_valid_lag_pairs_for_acf": MIN_ACF_PAIRS,
        "rolling_windows_sessions": list(ROLLING_WINDOWS),
        "periods": [
            {"name": name, "start": start, "end": end}
            for name, start, end in PERIODS
        ],
        "cross_sectional_dates": int(len(daily)),
        "acf_rows": int(len(acf)),
        "method_notes": [
            "Daily log returns are computed only across adjacent panel sessions with valid endpoints.",
            "Cross-sectional statistics use only finite returns on each date; n_securities records the effective cross-section size.",
            "MAD is the unscaled median absolute deviation around the cross-sectional median.",
            "ACF uses the global valid-series mean and variance with a pairwise-valid lag covariance numerator; only exact row-lag pairs are used.",
            "Rolling windows are measured in panel-date rows and require a complete window; no imputation is applied.",
            "Period and rolling summaries are descriptive, not structural-break tests or predictive evidence.",
            "Breadth shares are descriptive proportions, not trading signals.",
            "No feature selection, IC, models, forecasts, trading rules, or portfolio metrics.",
        ],
        "machine_outputs": [
            "daily_cross_sectional_metrics.csv",
            "run_metadata.json",
        ],
        "research_outputs": [
            "temporal_distribution_summary.csv",
            "yearly_summary.csv",
            "period_summary.csv",
            "rolling_summary.csv",
            "aggregate_acf_summary.csv",
            "EDA2_BLOCK_04_REPORT.md",
        ],
    })
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(
        args.docs_dir / "EDA2_BLOCK_04_REPORT.md",
        daily, metadata, time_summary, acf, rolling,
    )

    print("EDA2 Block 4 completed.")
    print(f"Return observations: {metadata['return_observations']:,}")
    print(f"Cross-sectional dates: {len(daily):,}")
    print(f"Machine outputs: {args.output_dir}")
    print(f"Research outputs: {args.docs_dir}")


if __name__ == "__main__":
    main()
