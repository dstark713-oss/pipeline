from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "eda2" / "block_02"
DEFAULT_DOCS = ROOT / "docs" / "research" / "eda2" / "results" / "block_02"

LAGS = (1, 2, 5, 10, 20)
LJUNG_BOX_LAGS = (5, 10, 20)
PERIODS = (
    ("2005_2012", "2005-01-01", "2012-12-31"),
    ("2013_2019", "2013-01-01", "2019-12-31"),
    ("2020_2026", "2020-01-01", "2026-12-31"),
)
MIN_CONTIGUOUS_OBS = 250
MIN_ACF_PAIRS = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EDA2 Block 2: temporal dependence of daily returns."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    parser.add_argument(
        "--min-contiguous-obs", type=int, default=MIN_CONTIGUOUS_OBS,
        help="Minimum length of the longest uninterrupted valid run for Ljung-Box.",
    )
    return parser.parse_args()


def load_returns(panel_path: Path) -> tuple[pd.DataFrame, dict]:
    """Build adjacent-panel-session log returns without filling or bridging gaps."""
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


def series_variants(values: np.ndarray) -> dict[str, np.ndarray]:
    x = np.asarray(values, dtype=np.float64)
    valid = np.isfinite(x)
    absolute = np.full_like(x, np.nan)
    squared = np.full_like(x, np.nan)
    absolute[valid] = np.abs(x[valid])
    squared[valid] = np.square(x[valid])
    return {"returns": x, "absolute_returns": absolute, "squared_returns": squared}


def pairwise_lag_correlation(values: np.ndarray, lag: int, min_pairs: int) -> tuple[float, int]:
    """Sample ACF: global centering/variance, pairwise-valid lag covariance."""
    x = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(x)
    if lag <= 0 or len(x) <= lag or finite.sum() < min_pairs:
        return np.nan, 0
    mean = float(np.mean(x[finite]))
    denominator = float(np.sum(np.square(x[finite] - mean)))
    if denominator <= 0:
        return np.nan, 0
    left, right = x[:-lag], x[lag:]
    valid = np.isfinite(left) & np.isfinite(right)
    n = int(valid.sum())
    if n < min_pairs:
        return np.nan, n
    covariance_numerator = float(
        np.sum((left[valid] - mean) * (right[valid] - mean))
    )
    return covariance_numerator / denominator, n


def longest_finite_run(values: np.ndarray) -> np.ndarray:
    """Return the longest contiguous run; missing panel sessions remain breaks."""
    valid = np.isfinite(values)
    if not valid.any():
        return np.array([], dtype=np.float64)
    padded = np.concatenate(([False], valid, [False])).astype(np.int8)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    lengths = ends - starts
    index = int(np.argmax(lengths))
    return np.asarray(values[starts[index]:ends[index]], dtype=np.float64)


def contiguous_acf(values: np.ndarray, max_lag: int) -> np.ndarray:
    """Conventional demeaned sample ACF for a complete uninterrupted segment."""
    x = np.asarray(values, dtype=np.float64)
    x = x[np.isfinite(x)]
    if len(x) <= max_lag or np.var(x) == 0:
        return np.full(max_lag, np.nan)
    centered = x - x.mean()
    denominator = float(np.dot(centered, centered))
    return np.asarray([
        float(np.dot(centered[:-lag], centered[lag:]) / denominator)
        for lag in range(1, max_lag + 1)
    ])


def ljung_box_from_acf(acf: np.ndarray, n_obs: int, max_lag: int) -> tuple[float, float]:
    if n_obs <= max_lag or len(acf) < max_lag or not np.isfinite(acf[:max_lag]).all():
        return np.nan, np.nan
    rho = acf[:max_lag]
    denominators = n_obs - np.arange(1, max_lag + 1)
    q_stat = float(n_obs * (n_obs + 2) * np.sum((rho * rho) / denominators))
    return q_stat, float(chi2.sf(q_stat, df=max_lag))


def benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    p = pd.to_numeric(p_values, errors="coerce")
    result = pd.Series(np.nan, index=p.index, dtype=np.float64)
    valid = p.notna()
    if not valid.any():
        return result
    raw = p.loc[valid].to_numpy(dtype=np.float64)
    order = np.argsort(raw)
    ranked = raw[order]
    m = len(ranked)
    adjusted = ranked * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    restored = np.empty(m, dtype=np.float64)
    restored[order] = adjusted
    result.loc[valid] = restored
    return result


def calculate_acf(
    returns: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    acf_rows: list[dict] = []
    periods = (("full_sample", None, None), *PERIODS)
    for period_name, start, end in periods:
        sample = returns if start is None else returns.loc[start:end]
        for secid in sample.columns:
            variants = series_variants(sample[secid].to_numpy(dtype=np.float64))
            for metric, values in variants.items():
                for lag in LAGS:
                    rho, n_pairs = pairwise_lag_correlation(values, lag, MIN_ACF_PAIRS)
                    acf_rows.append({
                        "period": period_name,
                        "secid": secid,
                        "metric": metric,
                        "lag": lag,
                        "acf": rho,
                        "valid_lag_pairs": n_pairs,
                        "valid_observations": int(np.isfinite(values).sum()),
                    })

    per_security = pd.DataFrame(acf_rows)
    summary_rows = []
    for (period, metric, lag), group in per_security.groupby(
        ["period", "metric", "lag"], sort=True
    ):
        x = group["acf"].dropna()
        summary_rows.append({
            "period": period,
            "metric": metric,
            "lag": int(lag),
            "n_securities": int(x.size),
            "mean_acf": float(x.mean()) if not x.empty else np.nan,
            "median_acf": float(x.median()) if not x.empty else np.nan,
            "q10_acf": float(x.quantile(0.10)) if not x.empty else np.nan,
            "q25_acf": float(x.quantile(0.25)) if not x.empty else np.nan,
            "q75_acf": float(x.quantile(0.75)) if not x.empty else np.nan,
            "q90_acf": float(x.quantile(0.90)) if not x.empty else np.nan,
            "positive_share": float((x > 0).mean()) if not x.empty else np.nan,
            "median_valid_lag_pairs": float(group["valid_lag_pairs"].median()),
        })
    summary = pd.DataFrame(summary_rows)
    full_summary = summary.loc[summary["period"] == "full_sample"].copy()
    period_summary = summary.loc[summary["period"] != "full_sample"].copy()
    return per_security, full_summary, period_summary


def calculate_ljung_box(
    returns: pd.DataFrame, min_contiguous_obs: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict] = []
    for secid in returns.columns:
        variants = series_variants(returns[secid].to_numpy(dtype=np.float64))
        for metric, values in variants.items():
            run = longest_finite_run(values)
            n_run = int(len(run))
            acf = contiguous_acf(run, max(LJUNG_BOX_LAGS)) if n_run else np.array([])
            total_valid = int(np.isfinite(values).sum())
            for test_lag in LJUNG_BOX_LAGS:
                if n_run < min_contiguous_obs:
                    q_stat, p_value = np.nan, np.nan
                else:
                    q_stat, p_value = ljung_box_from_acf(acf, n_run, test_lag)
                rows.append({
                    "secid": secid,
                    "metric": metric,
                    "test_lag": int(test_lag),
                    "longest_contiguous_run": n_run,
                    "total_valid_observations": total_valid,
                    "run_share_of_valid": float(n_run / total_valid) if total_valid else np.nan,
                    "q_statistic": q_stat,
                    "p_value": p_value,
                })

    results = pd.DataFrame(rows)
    results["q_value_bh"] = np.nan
    for (_, _), indices in results.groupby(["metric", "test_lag"]).groups.items():
        results.loc[indices, "q_value_bh"] = benjamini_hochberg(
            results.loc[indices, "p_value"]
        )

    summary_rows = []
    for (metric, test_lag), group in results.groupby(["metric", "test_lag"]):
        tested = group.dropna(subset=["p_value"])
        summary_rows.append({
            "metric": metric,
            "test_lag": int(test_lag),
            "n_securities_total": int(len(group)),
            "n_tested": int(len(tested)),
            "median_longest_run_tested": float(tested["longest_contiguous_run"].median()) if not tested.empty else np.nan,
            "median_q_statistic": float(tested["q_statistic"].median()) if not tested.empty else np.nan,
            "raw_significant_5pct": int((tested["p_value"] < 0.05).sum()),
            "bh_significant_5pct": int((tested["q_value_bh"] < 0.05).sum()),
            "bh_significant_share": float((tested["q_value_bh"] < 0.05).mean()) if not tested.empty else np.nan,
        })
    return results, pd.DataFrame(summary_rows)


def write_report(
    path: Path,
    returns: pd.DataFrame,
    metadata: dict,
    acf_summary: pd.DataFrame,
    period_summary: pd.DataFrame,
    lb_summary: pd.DataFrame,
) -> None:
    lines = [
        "# EDA2 — Блок 2. Временная зависимость",
        "",
        "## Область анализа",
        f"- Дат панели: {metadata['panel_dates']:,}",
        f"- Дат доходностей: {len(returns):,}",
        f"- Бумаг: {len(returns.columns):,}",
        f"- Валидных наблюдений доходности: {metadata['return_observations']:,}",
        f"- Период: {returns.index.min().date()} — {returns.index.max().date()}",
        "- Ряды: доходности, абсолютные доходности и квадраты доходностей.",
        f"- Лаги ACF: {', '.join(map(str, LAGS))}.",
        "",
        "## ACF: полная выборка",
        "В таблице приведены межбумажные распределения оценок ACF. "
        "Каждая оценка использует только пары наблюдений, разделённые ровно заданным числом строк календаря панели.",
        "",
        "| Ряд | Лаг | Бумаг | Медиана ACF | Q10 | Q90 | Доля ACF > 0 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in acf_summary.itertuples(index=False):
        lines.append(
            f"| {row.metric} | {row.lag} | {row.n_securities} | "
            f"{row.median_acf:.5f} | {row.q10_acf:.5f} | "
            f"{row.q90_acf:.5f} | {row.positive_share:.3f} |"
        )

    lines.extend([
        "",
        "## Сопоставление временных периодов",
        "Периоды заданы заранее: 2005–2012, 2013–2019 и 2020–2026. "
        "Последний период включает неполный 2026 год. Значения являются описательными.",
        "",
        "| Период | Ряд | Лаг | Бумаг | Медиана ACF | Q10 | Q90 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in period_summary.itertuples(index=False):
        lines.append(
            f"| {row.period} | {row.metric} | {row.lag} | {row.n_securities} | "
            f"{row.median_acf:.5f} | {row.q10_acf:.5f} | {row.q90_acf:.5f} |"
        )

    lines.extend([
        "",
        "## Ljung–Box",
        f"Минимальная длина непрерывного участка: {metadata['min_contiguous_obs']} наблюдений. "
        "Тесты считаются только на самом длинном непрерывном участке каждой бумаги; "
        "пропуски не удаляются с последующим склеиванием временных участков.",
        "",
        "| Ряд | Максимальный лаг | Протестировано | Медиана Q | BH значимо (5%) | Доля BH значимых |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in lb_summary.itertuples(index=False):
        median_q = f"{row.median_q_statistic:.3f}" if pd.notna(row.median_q_statistic) else "NA"
        share = f"{row.bh_significant_share:.3f}" if pd.notna(row.bh_significant_share) else "NA"
        lines.append(
            f"| {row.metric} | {row.test_lag} | {row.n_tested} | {median_q} | "
            f"{row.bh_significant_5pct} | {share} |"
        )

    lines.extend([
        "",
        "## Методологические ограничения",
        "- ACF по полной выборке использует общее среднее и знаменатель дисперсии валидного ряда, а в числителе — только валидные пары, разделённые ровно lag строками панели; пропуски не заполняются.",
        "- Ljung–Box рассчитывается отдельно на самом длинном непрерывном валидном участке. Поэтому тест может охватывать только часть доступной истории бумаги.",
        "- Стандартная асимптотическая калибровка Ljung–Box применяется к непрерывному участку; результаты не переносятся автоматически на всю разреженную историю бумаги.",
        "- BH-коррекция выполняется отдельно для каждого сочетания ряда и максимального лага по протестированным бумагам.",
        "- Статистическая значимость не равна большой величине эффекта и не доказывает предсказательную или экономическую полезность.",
        "- Сопоставление периодов описательное; различия не являются формальным тестом структурного сдвига.",
        "- Нет моделей, прогнозов, IC, отбора признаков, торговых правил или портфельных метрик.",
        "",
        "## Файлы",
        "- per_security_acf.csv (машинный)",
        "- ljung_box_per_security.csv (машинный)",
        "- acf_distribution_summary.csv",
        "- period_acf_summary.csv",
        "- ljung_box_summary.csv",
        "- EDA2_BLOCK_02_REPORT.md",
        "",
        "Числа в отчёте формируются только после фактического локального запуска скрипта.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.min_contiguous_obs <= max(LJUNG_BOX_LAGS):
        raise ValueError("--min-contiguous-obs must exceed the maximum Ljung-Box lag.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)

    returns, metadata = load_returns(args.panel)
    acf_per_security, acf_summary, period_summary = calculate_acf(returns)
    lb_per_security, lb_summary = calculate_ljung_box(
        returns, args.min_contiguous_obs
    )

    acf_per_security.to_csv(args.output_dir / "per_security_acf.csv", index=False)
    lb_per_security.to_csv(
        args.output_dir / "ljung_box_per_security.csv", index=False
    )
    acf_summary.to_csv(args.docs_dir / "acf_distribution_summary.csv", index=False)
    period_summary.to_csv(args.docs_dir / "period_acf_summary.csv", index=False)
    lb_summary.to_csv(args.docs_dir / "ljung_box_summary.csv", index=False)

    metadata.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "block": 2,
        "block_name": "Временная зависимость",
        "acf_lags": list(LAGS),
        "min_valid_lag_pairs_for_acf": MIN_ACF_PAIRS,
        "ljung_box_max_lags": list(LJUNG_BOX_LAGS),
        "min_contiguous_obs_for_ljung_box": args.min_contiguous_obs,
        "periods": [
            {"name": name, "start": start, "end": end}
            for name, start, end in PERIODS
        ],
        "acf_security_rows": int(len(acf_per_security)),
        "ljung_box_security_rows": int(len(lb_per_security)),
        "ljung_box_tested_rows": int(lb_per_security["p_value"].notna().sum()),
        "method_notes": [
            "Returns are computed only between adjacent panel sessions with valid endpoints.",
            "No forward-fill, zero imputation, or bridging over missing sessions.",
            "Full-sample ACF uses the global valid-series mean and variance with a pairwise-valid lag covariance numerator; at least 60 lag pairs are required.",
            "Ljung-Box is evaluated only on each security-series' longest uninterrupted valid run.",
            "Ljung-Box p-values use the chi-square approximation with degrees of freedom equal to the tested maximum lag.",
            "BH correction is applied separately for each series and maximum lag across tested securities.",
            "Period comparisons are descriptive and include incomplete 2026.",
            "No predictive model, IC, feature selection, trading rule, or portfolio metric.",
        ],
        "machine_outputs": [
            "per_security_acf.csv",
            "ljung_box_per_security.csv",
            "run_metadata.json",
        ],
        "research_outputs": [
            "acf_distribution_summary.csv",
            "period_acf_summary.csv",
            "ljung_box_summary.csv",
            "EDA2_BLOCK_02_REPORT.md",
        ],
    })
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(
        args.docs_dir / "EDA2_BLOCK_02_REPORT.md",
        returns, metadata, acf_summary, period_summary, lb_summary,
    )

    print("EDA2 Block 2 completed.")
    print(f"Return observations: {metadata['return_observations']:,}")
    print(f"Return dates: {metadata['return_dates']:,}")
    print(f"Securities: {metadata['panel_tickers']:,}")
    print(f"Ljung-Box tests calculated: {metadata['ljung_box_tested_rows']:,}")
    print(f"Machine outputs: {args.output_dir}")
    print(f"Research outputs: {args.docs_dir}")


if __name__ == "__main__":
    main()
