from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "data/processed/top50/top50_panel.parquet"
DEFAULT_OUTPUT = ROOT / "data/interim/eda2/block_07"
DEFAULT_DOCS = ROOT / "docs/research/eda2/results/block_07"
PERIODS = (
    ("2005_2012", "2005-01-01", "2012-12-31"),
    ("2013_2019", "2013-01-01", "2019-12-31"),
    ("2020_2026", "2020-01-01", "2026-12-31"),
)
ACTIVITY_COLUMNS = ("volume", "value", "value_60d")
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def parse_args():
    parser = argparse.ArgumentParser(
        description="EDA2 Block 7: trading activity, concentration and conditional distributions."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    return parser.parse_args()


def load_panel(path: Path) -> tuple[pd.DataFrame, dict]:
    columns = [
        "tradedate", "secid", "rank", "universe_size", "value_60d",
        "volume", "value", "adjusted_close", "bar_available",
    ]
    panel = pd.read_parquet(path, columns=columns)
    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.upper()
    numeric = [
        "rank", "universe_size", "value_60d", "volume", "value",
        "adjusted_close", "bar_available",
    ]
    for column in numeric:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    panel = panel.dropna(subset=["tradedate", "secid", "rank"]).copy()
    panel = panel.sort_values(["tradedate", "rank", "secid"]).reset_index(drop=True)
    if panel.empty:
        raise ValueError("TOP50 panel is empty.")
    if panel.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate (tradedate, secid) rows in panel.")
    if not panel["rank"].between(1, 50).all():
        raise ValueError("PIT rank outside TOP50 range.")
    for column in ACTIVITY_COLUMNS:
        values = panel[column].to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError(f"Infinite values found in {column}.")
        finite = panel[column].dropna()
        if (finite < 0).any():
            raise ValueError(f"Negative activity found in {column}.")
    panel["return"] = np.nan
    panel["return_valid"] = False
    dates = pd.DatetimeIndex(sorted(panel["tradedate"].unique()))
    close = panel.pivot(index="tradedate", columns="secid", values="adjusted_close").reindex(dates)
    available = panel.pivot(index="tradedate", columns="secid", values="bar_available").reindex(dates)
    valid_close = close.where((available == 1) & (close > 0))
    returns = np.log(valid_close / valid_close.shift(1))
    returns = returns.replace([np.inf, -np.inf], np.nan)
    return_map = returns.stack().rename("return").reset_index()
    return_map.columns = ["tradedate", "secid", "return"]
    panel = panel.drop(columns=["return", "return_valid"]).merge(
        return_map, on=["tradedate", "secid"], how="left", validate="one_to_one"
    )
    meta = {
        "panel_path": str(path),
        "rows": int(len(panel)),
        "dates": int(panel["tradedate"].nunique()),
        "securities": int(panel["secid"].nunique()),
        "sample_start": str(panel["tradedate"].min().date()),
        "sample_end": str(panel["tradedate"].max().date()),
        "valid_current_returns": int(panel["return"].notna().sum()),
        "return_rule": "Log adjusted-close return between adjacent panel sessions; both endpoints require bar_available=1 and positive adjusted_close; no filling or stitching.",
    }
    return panel, meta


def distribution_summary(frame: pd.DataFrame, group_columns: list[str], value_column: str) -> pd.DataFrame:
    rows = []
    grouped = frame.groupby(group_columns, dropna=False) if group_columns else [((), frame)]
    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        x = pd.to_numeric(group[value_column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if x.empty:
            continue
        row = {name: value for name, value in zip(group_columns, key)}
        row.update({
            "observations": int(x.size),
            "mean": x.mean(),
            "median": x.median(),
            "std": x.std(ddof=1),
            "mad": (x - x.median()).abs().median(),
            "iqr": x.quantile(.75) - x.quantile(.25),
            "zero_share": x.eq(0).mean(),
            "positive_share": x.gt(0).mean(),
        })
        for q in QUANTILES:
            row[f"q{int(q * 100):02d}"] = x.quantile(q)
        rows.append(row)
    return pd.DataFrame(rows)


def period_label(dates: pd.Series) -> pd.Series:
    result = pd.Series("outside_defined_periods", index=dates.index, dtype="object")
    for name, start, end in PERIODS:
        result.loc[dates.between(start, end)] = name
    return result


def activity_distributions(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pooled_rows, security_rows, period_rows = [], [], []
    for column in ACTIVITY_COLUMNS:
        pooled = distribution_summary(panel, [], column)
        if not pooled.empty:
            pooled.insert(0, "activity", column)
            pooled_rows.append(pooled)
        per_security = distribution_summary(panel, ["secid"], column)
        if not per_security.empty:
            per_security.insert(0, "activity", column)
            security_rows.append(per_security)
        temp = panel[["tradedate", column]].copy()
        temp["period"] = period_label(temp["tradedate"])
        period = distribution_summary(temp, ["period"], column)
        if not period.empty:
            period.insert(0, "activity", column)
            period_rows.append(period)
    return (
        pd.concat(pooled_rows, ignore_index=True),
        pd.concat(security_rows, ignore_index=True),
        pd.concat(period_rows, ignore_index=True),
    )


def concentration_by_date(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, group in panel.groupby("tradedate", sort=True):
        row = {"tradedate": date, "universe_size": int(group["secid"].nunique())}
        for column in ("value", "volume"):
            x = pd.to_numeric(group[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
            x = x.where(x > 0).dropna()
            total = x.sum()
            if x.empty or not np.isfinite(total) or total <= 0:
                row.update({
                    f"{column}_valid_securities": int(x.size),
                    f"{column}_top5_share": np.nan,
                    f"{column}_top10_share": np.nan,
                    f"{column}_hhi": np.nan,
                })
                continue
            shares = (x / total).sort_values(ascending=False)
            row.update({
                f"{column}_valid_securities": int(x.size),
                f"{column}_top5_share": shares.head(5).sum(),
                f"{column}_top10_share": shares.head(10).sum(),
                f"{column}_hhi": (shares ** 2).sum(),
            })
        rows.append(row)
    return pd.DataFrame(rows)


def concentration_summaries(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [
        "value_top5_share", "value_top10_share", "value_hhi",
        "volume_top5_share", "volume_top10_share", "volume_hhi",
        "value_valid_securities", "volume_valid_securities",
    ]
    overall, yearly = [], []
    for metric in metrics:
        x = daily[metric].dropna()
        if not x.empty:
            overall.append({
                "metric": metric, "sessions": len(x), "mean": x.mean(),
                "median": x.median(), "q10": x.quantile(.10),
                "q25": x.quantile(.25), "q75": x.quantile(.75),
                "q90": x.quantile(.90),
            })
        temp = daily[["tradedate", metric]].dropna().copy()
        temp["year"] = temp["tradedate"].dt.year
        for year, group in temp.groupby("year"):
            values = group[metric]
            yearly.append({
                "metric": metric, "year": int(year), "sessions": len(values),
                "median": values.median(), "q25": values.quantile(.25),
                "q75": values.quantile(.75), "q10": values.quantile(.10),
                "q90": values.quantile(.90),
            })
    return pd.DataFrame(overall), pd.DataFrame(yearly)


def assign_daily_terciles(frame: pd.DataFrame, column: str) -> pd.Series:
    result = pd.Series(index=frame.index, dtype="object")
    for _, indices in frame.groupby("tradedate").groups.items():
        values = frame.loc[indices, column]
        valid = values.notna() & np.isfinite(values) & values.ge(0)
        if valid.sum() < 3:
            continue
        # Rank first so tied activity values do not collapse qcut bins.
        percentile = values.loc[valid].rank(method="average", pct=True)
        labels = pd.cut(
            percentile,
            bins=[0, 1 / 3, 2 / 3, 1],
            labels=["low", "mid", "high"],
            include_lowest=True,
        )
        result.loc[labels.index] = labels.astype(str)
    return result


def conditional_summary(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = panel.loc[panel["return"].notna()].copy()
    data["period"] = period_label(data["tradedate"])
    rows = []
    # Dynamic, within-date activity terciles.
    for activity in ("value", "volume"):
        group_column = f"{activity}_tercile"
        data[group_column] = assign_daily_terciles(data, activity)
        summary = distribution_summary(
            data.dropna(subset=[group_column]), ["period", group_column], "return"
        )
        if not summary.empty:
            summary = summary.rename(columns={group_column: "group"})
            summary.insert(0, "conditioning_axis", f"daily_{activity}")
            rows.append(summary)
    # Structural PIT rank groups. value_60d is the ranking basis, not an independent axis.
    data["rank_group"] = pd.cut(
        data["rank"], bins=[0, 10, 25, 50],
        labels=["1-10", "11-25", "26-50"], include_lowest=True,
    ).astype("object")
    rank_summary = distribution_summary(data, ["period", "rank_group"], "return")
    if not rank_summary.empty:
        rank_summary = rank_summary.rename(columns={"rank_group": "group"})
        rank_summary.insert(0, "conditioning_axis", "pit_rank_value60d")
        rows.append(rank_summary)
    all_summary = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    by_date_rows = []
    for date, group in data.groupby("tradedate"):
        for group_column in ("value_tercile", "volume_tercile", "rank_group"):
            if group_column not in group:
                continue
            for label, part in group.dropna(subset=[group_column]).groupby(group_column):
                returns = part["return"].dropna()
                if returns.empty:
                    continue
                by_date_rows.append({
                    "tradedate": date, "conditioning_axis": group_column,
                    "group": str(label), "n_securities": len(part),
                    "mean_return": returns.mean(), "median_return": returns.median(),
                    "std_return": returns.std(ddof=1),
                    "mad_return": (returns - returns.median()).abs().median(),
                })
    return all_summary, pd.DataFrame(by_date_rows)


def write_report(path: Path, meta: dict, pooled: pd.DataFrame,
                 concentration: pd.DataFrame, conditional: pd.DataFrame) -> None:
    lines = [
        "# EDA2 — Блок 7. Торговая активность, концентрация и условная структура", "",
        "## Выборка",
        f"- Строк панели: {meta['rows']:,}; дат: {meta['dates']:,}; бумаг: {meta['securities']:,}.",
        f"- Период: {meta['sample_start']} — {meta['sample_end']}.",
        f"- Валидных текущих доходностей: {meta['valid_current_returns']:,}.",
        "- Анализ ограничен PIT TOP50. Концентрация не описывает весь российский рынок.", "",
        "## Распределения торговой активности",
        "Pooled-статистики взвешивают строки «бумага-дата»; отдельная таблица содержит распределения статистик по бумагам.",
        "", "| Активность | N | Mean | Median | Std | MAD | IQR | Zero share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in pooled.itertuples(index=False):
        lines.append(
            f"| {r.activity} | {r.observations:,} | {r.mean:.4g} | {r.median:.4g} | "
            f"{r.std:.4g} | {r.mad:.4g} | {r.iqr:.4g} | {r.zero_share:.1%} |"
        )
    lines += [
        "", "## Концентрация активности внутри PIT TOP50",
        "HHI = сумма квадратов долей активности; выше означает большую концентрацию.",
        "", "| Метрика | Сессий | Median | Q10 | Q25 | Q75 | Q90 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in concentration.itertuples(index=False):
        lines.append(
            f"| {r.metric} | {r.sessions:,} | {r.median:.4g} | {r.q10:.4g} | "
            f"{r.q25:.4g} | {r.q75:.4g} | {r.q90:.4g} |"
        )
    lines += [
        "", "## Условные распределения текущих доходностей",
        "Текущая доходность рассчитана между соседними датами панели при наличии валидных баров на обеих датах. Будущие доходности не используются.",
        "Дневные terciles строятся внутри каждого сечения отдельно. PIT rank groups: 1–10, 11–25, 26–50.",
        "PIT rank и value_60d — одна связанная ось, поскольку ранг построен по value_60d.",
        "", "| Ось | Период | Группа | N | Mean | Median | Std | MAD | Q05 | Q95 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in conditional.itertuples(index=False):
        lines.append(
            f"| {r.conditioning_axis} | {r.period} | {r.group} | "
            f"{r.observations:,} | {r.mean:.4%} | {r.median:.4%} | {r.std:.4%} | "
            f"{r.mad:.4%} | {r.q05:.4%} | {r.q95:.4%} |"
        )
    lines += [
        "", "## Ограничения интерпретации",
        "- Условные распределения описывают совместную структуру, но не устанавливают причинность или предсказательную способность.",
        "- Дневные группы активности являются относительными внутри текущего PIT-сечения; границы меняются от даты к дате.",
        "- Ранговые группы и value_60d не являются независимыми характеристиками.",
        "- Результаты относятся только к бумагам, входящим в PIT TOP50 на соответствующую дату.",
        "- Не рассчитываются IC, модели, feature importance, будущие доходности, торговые сигналы или портфельные выводы.",
        "", "## Outputs",
        "- activity_pooled_summary.csv; activity_per_security_summary.csv; activity_period_summary.csv",
        "- daily_activity_concentration.csv; concentration_overall_summary.csv; concentration_yearly_summary.csv",
        "- conditional_return_summary.csv; conditional_return_by_date.csv; run_metadata.json",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)
    panel, meta = load_panel(args.panel)
    pooled, per_security, activity_period = activity_distributions(panel)
    daily_concentration = concentration_by_date(panel)
    concentration, concentration_yearly = concentration_summaries(daily_concentration)
    conditional, conditional_daily = conditional_summary(panel)

    daily_concentration.to_csv(args.output_dir / "daily_activity_concentration.csv", index=False)
    conditional_daily.to_csv(args.output_dir / "conditional_return_by_date.csv", index=False)
    metadata = {
        **meta, "created_at_utc": datetime.now(timezone.utc).isoformat(), "block": 7,
        "activity_columns": list(ACTIVITY_COLUMNS),
        "concentration_scope": "PIT TOP50 only; positive valid activity within each date.",
        "concentration_metrics": ["top5_share", "top10_share", "HHI"],
        "conditional_groups": {
            "daily_activity": ["low", "mid", "high"],
            "pit_rank": ["1-10", "11-25", "26-50"],
        },
        "pit_rank_value60d_relationship": "rank is derived from trailing 60-session VALUE; not treated as an independent characteristic.",
        "future_returns_used": False,
        "numtrades_used": False,
        "models_or_ic_used": False,
    }
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pooled.to_csv(args.docs_dir / "activity_pooled_summary.csv", index=False)
    per_security.to_csv(args.docs_dir / "activity_per_security_summary.csv", index=False)
    activity_period.to_csv(args.docs_dir / "activity_period_summary.csv", index=False)
    concentration.to_csv(args.docs_dir / "concentration_overall_summary.csv", index=False)
    concentration_yearly.to_csv(args.docs_dir / "concentration_yearly_summary.csv", index=False)
    conditional.to_csv(args.docs_dir / "conditional_return_summary.csv", index=False)
    write_report(args.docs_dir / "EDA2_BLOCK_07_REPORT.md", meta, pooled, concentration, conditional)
    print("EDA2 Block 7 completed.")
    print(f"Panel rows: {len(panel):,}; conditional groups: {len(conditional):,}")
    print(f"Machine outputs: {args.output_dir}")
    print(f"Research outputs: {args.docs_dir}")


if __name__ == "__main__":
    main()
