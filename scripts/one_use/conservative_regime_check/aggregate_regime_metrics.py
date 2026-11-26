from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "data" / "interim" / "one_use" / "regime_check" / "daily_regime_metrics.csv"
DEFAULT_OUT = ROOT / "data" / "interim" / "one_use" / "regime_check" / "aggregated"


METRICS = [
    "n_valid", "breadth_positive", "breadth_negative", "equal_weight_return",
    "median_return", "cross_sectional_std", "positive_return_share_top1",
    "positive_return_share_top5", "positive_return_share_top10",
    "positive_return_hhi",
]


def args_parser() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate daily conservative regime diagnostics into readable reports.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--windows", default="20,60,120,250",
                   help="Trailing session windows, comma-separated.")
    p.add_argument("--breadth-thresholds", default="0.4,0.5,0.6")
    return p.parse_args()


def load_daily(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Daily metrics file not found: {path}")
    df = pd.read_csv(path)
    required = {"tradedate", *METRICS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df["tradedate"] = pd.to_datetime(df["tradedate"], errors="coerce")
    df = df.dropna(subset=["tradedate"]).sort_values("tradedate").reset_index(drop=True)
    if df["tradedate"].duplicated().any():
        raise ValueError("Duplicate tradedate rows.")
    for col in METRICS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df.empty:
        raise ValueError("Input contains no daily observations.")
    return df


def summarize(g: pd.DataFrame, label: str, kind: str) -> dict:
    row = {
        "period": label,
        "period_type": kind,
        "start": g["tradedate"].min().date().isoformat(),
        "end": g["tradedate"].max().date().isoformat(),
        "n_sessions": len(g),
    }
    for col in METRICS:
        s = g[col].dropna()
        if s.empty:
            continue
        row[f"{col}_mean"] = s.mean()
        row[f"{col}_median"] = s.median()
        row[f"{col}_p10"] = s.quantile(0.10)
        row[f"{col}_p90"] = s.quantile(0.90)
    row["share_sessions_breadth_gt_50pct"] = (g["breadth_positive"] > 0.5).mean()
    row["share_sessions_breadth_lt_40pct"] = (g["breadth_positive"] < 0.4).mean()
    row["share_sessions_top5_share_gt_70pct"] = (g["positive_return_share_top5"] > 0.7).mean()
    row["share_sessions_top10_share_gt_85pct"] = (g["positive_return_share_top10"] > 0.85).mean()
    return row


def build_periods(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    rows = [summarize(df, "full_sample", "full_sample")]
    for year, g in df.groupby(df["tradedate"].dt.year):
        rows.append(summarize(g, str(year), "calendar_year"))
    for quarter, g in df.groupby(df["tradedate"].dt.to_period("Q")):
        rows.append(summarize(g, str(quarter), "calendar_quarter"))
    for n in windows:
        g = df.tail(n)
        if len(g):
            rows.append(summarize(g, f"last_{n}_sessions", "rolling_window"))
    return pd.DataFrame(rows)


def build_latest(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    latest = df.iloc[-1]
    rows = []
    for metric in METRICS:
        rows.append({
            "metric": metric,
            "latest_date": latest["tradedate"].date().isoformat(),
            "latest_value": latest[metric],
            "last_20_mean": df.tail(20)[metric].mean(),
            "last_60_mean": df.tail(60)[metric].mean(),
            "last_120_mean": df.tail(120)[metric].mean(),
            "full_sample_mean": df[metric].mean(),
        })
    return pd.DataFrame(rows)


def build_thresholds(df: pd.DataFrame, thresholds: list[float]) -> pd.DataFrame:
    rows = []
    for threshold in thresholds:
        state = df["breadth_positive"] >= threshold
        # Identify contiguous runs in observed session sequence.
        group = state.ne(state.shift()).cumsum()
        episodes = df.loc[state].assign(_episode=group[state]).groupby("_episode")
        durations = episodes.size()
        rows.append({
            "breadth_threshold": threshold,
            "share_all_sessions": state.mean(),
            "episode_count": len(durations),
            "median_episode_sessions": durations.median() if len(durations) else 0,
            "max_episode_sessions": durations.max() if len(durations) else 0,
            "current_streak_sessions": int((state.iloc[::-1].cumprod()).sum()),
            "currently_above_threshold": bool(state.iloc[-1]),
        })
    return pd.DataFrame(rows)


def build_monthly(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index("tradedate")
    monthly = x.resample("ME").agg({
        "n_valid": "mean",
        "breadth_positive": "mean",
        "breadth_negative": "mean",
        "equal_weight_return": "mean",
        "median_return": "mean",
        "positive_return_share_top5": "mean",
        "positive_return_share_top10": "mean",
        "positive_return_hhi": "mean",
    }).dropna(how="all").reset_index()
    return monthly


def build_report(df: pd.DataFrame, periods: pd.DataFrame, latest: pd.DataFrame,
                 thresholds: pd.DataFrame) -> str:
    end = df["tradedate"].max().date().isoformat()
    start = df["tradedate"].min().date().isoformat()
    full = periods.loc[periods["period"] == "full_sample"].iloc[0]
    recent = periods[periods["period"] == "last_120_sessions"]
    recent_line = ""
    if not recent.empty:
        r = recent.iloc[0]
        recent_line = (
            f"- Последние 120 сессий: breadth={r.get('breadth_positive_mean', np.nan):.1%}, "
            f"equal-weight mean daily return={r.get('equal_weight_return_mean', np.nan):.3%}, "
            f"median daily return={r.get('median_return_mean', np.nan):.3%}, "
            f"top-5 positive contribution share={r.get('positive_return_share_top5_mean', np.nan):.1%}.\n"
        )
    lines = [
        "# Conservative regime diagnostics: aggregate report", "",
        f"Период данных: {start} — {end}; наблюдений: {len(df)} торговых сессий.", "",
        "## Полная выборка",
        f"- Средний breadth: {full.get('breadth_positive_mean', np.nan):.1%}.",
        f"- Средняя equal-weight доходность за сессию: {full.get('equal_weight_return_mean', np.nan):.3%}.",
        f"- Средняя медианная доходность за сессию: {full.get('median_return_mean', np.nan):.3%}.",
        f"- Средняя доля топ-5 среди положительных вкладов: {full.get('positive_return_share_top5_mean', np.nan):.1%}.",
        f"- Средняя доля топ-10 среди положительных вкладов: {full.get('positive_return_share_top10_mean', np.nan):.1%}.",
        "", "## Последний период", recent_line.rstrip() if recent_line else "- Недостаточно данных для 120 сессий.", "",
        "## Текущие серии breadth",
        thresholds.to_markdown(index=False), "",
        "## Последние значения и сравнение с историей",
        latest.to_markdown(index=False), "",
        "## Интерпретационные ограничения",
        "- Это описательная агрегация, не статистический тест гипотезы и не торговый сигнал.",
        "- TOP50 equal-weight breadth не является IMOEX breadth.",
        "- Доли top-k относятся только к положительным доходностям внутри сечения.",
        "- Сравнение последних окон с полной историей не контролирует структурные изменения состава рынка.",
        "- Фундаментальные причины по этим данным не устанавливаются.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = args_parser()
    windows = sorted({int(x.strip()) for x in args.windows.split(",") if x.strip()})
    thresholds = sorted({float(x.strip()) for x in args.breadth_thresholds.split(",") if x.strip()})
    if any(n <= 0 for n in windows):
        raise ValueError("Window sizes must be positive.")
    if any(t < 0 or t > 1 for t in thresholds):
        raise ValueError("Breadth thresholds must be between 0 and 1.")

    df = load_daily(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    periods = build_periods(df, windows)
    latest = build_latest(df, windows)
    threshold_table = build_thresholds(df, thresholds)
    monthly = build_monthly(df)

    periods.to_csv(args.output_dir / "period_aggregates.csv", index=False, encoding="utf-8-sig")
    latest.to_csv(args.output_dir / "latest_vs_history.csv", index=False, encoding="utf-8-sig")
    threshold_table.to_csv(args.output_dir / "breadth_episodes.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(args.output_dir / "monthly_aggregates.csv", index=False, encoding="utf-8-sig")
    report = build_report(df, periods, latest, threshold_table)
    (args.output_dir / "AGGREGATE_REPORT.md").write_text(report, encoding="utf-8")

    meta = {
        "input": str(args.input.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "sessions": len(df),
        "start": df["tradedate"].min().date().isoformat(),
        "end": df["tradedate"].max().date().isoformat(),
        "windows": windows,
        "breadth_thresholds": thresholds,
        "outputs": [
            "AGGREGATE_REPORT.md", "period_aggregates.csv",
            "latest_vs_history.csv", "breadth_episodes.csv", "monthly_aggregates.csv"
        ],
        "no_signal_generated": True,
    }
    (args.output_dir / "aggregate_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(report)
    print(f"\nAggregate outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
