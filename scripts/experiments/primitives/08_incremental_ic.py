
# pipeline/scripts/experiments/primitives/08_incremental_ic.py

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

PANEL_PATH = ROOT / "data/processed/top50/top50_panel.parquet"
FEATURES_PATH = ROOT / "data/interim/primitive_research/primitive_features.parquet"
DB_PATH = ROOT / "data/processed/moex_daily_adjusted.sqlite"

OUT_DIR = ROOT / "data/interim/primitive_research/incremental_ic"

TABLE = "adjusted_daily_bars"

FEATURES = [
    "drawdown_60",
    "zscore_sma20_20",
    "positive_turnover_share_20",
    "realized_vol_60",
    "drawdown_20",
    "realized_vol_20",
    "return_20",
    "price_sma20",
]

HORIZONS = [5, 10, 20]
MIN_CROSS_SECTION = 20

PERIODS = {
    "2005-2012": ("2005-01-01", "2012-12-31"),
    "2013-2019": ("2013-01-01", "2019-12-31"),
    "2020-2026": ("2020-01-01", "2026-12-31"),
}


def log(message: str) -> None:
    print(f"[INFO] {message}")


def normalize_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


def normalize_secids(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def find_column(columns, candidates):
    lookup = {str(c).lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    raise ValueError(
        f"Не найдена колонка из {candidates}. "
        f"Доступные колонки: {list(columns)}"
    )


def load_inputs():
    for path in [PANEL_PATH, FEATURES_PATH, DB_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"Не найден файл: {path}")

    panel = pd.read_parquet(PANEL_PATH)
    features = pd.read_parquet(FEATURES_PATH)

    panel_date = find_column(panel.columns, ["tradedate", "trade_date"])
    feature_date = find_column(features.columns, ["tradedate", "trade_date"])
    feature_secid = find_column(features.columns, ["secid", "ticker"])

    panel = panel.rename(columns={panel_date: "tradedate"})
    features = features.rename(
        columns={
            feature_date: "tradedate",
            feature_secid: "secid",
        }
    )

    panel["tradedate"] = normalize_dates(panel["tradedate"])
    features["tradedate"] = normalize_dates(features["tradedate"])
    features["secid"] = normalize_secids(features["secid"])

    panel = panel.dropna(subset=["tradedate"])
    features = features.dropna(subset=["tradedate", "secid"])

    missing_features = [
        feature for feature in FEATURES
        if feature not in features.columns
    ]

    if missing_features:
        raise ValueError(
            f"В primitive_features.parquet отсутствуют признаки: "
            f"{missing_features}"
        )

    calendar = sorted(panel["tradedate"].dropna().unique().tolist())

    if not calendar:
        raise ValueError("Не удалось получить торговый календарь из панели.")

    features = features[
        ["tradedate", "secid"] + FEATURES
    ].copy()

    features = features.drop_duplicates(
        subset=["tradedate", "secid"],
        keep="first",
    )

    log(f"Торговых дат в календаре: {len(calendar):,}")
    log(f"Строк с признаками: {len(features):,}")
    log(f"Уникальных SECID: {features['secid'].nunique():,}")

    return panel, features, calendar


def load_adjusted_bars(secids: list[str]) -> pd.DataFrame:
    """
    Загружает OHLC из adjusted_daily_bars.
    Для одной бумаги и даты выбирает валидный TQBR,
    а при его отсутствии валидный EQBR.
    Исходную БД не изменяет.
    """

    log("Загрузка adjusted OHLC для выбранных SECID...")

    connection = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        schema = pd.read_sql_query(
            f"PRAGMA table_info({TABLE})",
            connection,
        )

        columns = schema["name"].tolist()

        secid_col = find_column(columns, ["secid"])
        date_col = find_column(columns, ["tradedate"])
        board_col = find_column(columns, ["boardid"])
        open_col = find_column(columns, ["open"])
        close_col = find_column(columns, ["close"])

        selected_columns = [
            secid_col,
            date_col,
            board_col,
            open_col,
            close_col,
        ]

        quoted = ", ".join(
            f'"{column}"' for column in selected_columns
        )

        chunks = []

        unique_secids = sorted(set(secids))

        for start in range(0, len(unique_secids), 400):
            batch = unique_secids[start:start + 400]
            placeholders = ",".join(["?"] * len(batch))

            sql = f"""
                SELECT {quoted}
                FROM {TABLE}
                WHERE UPPER(TRIM("{secid_col}")) IN ({placeholders})
                  AND UPPER(TRIM("{board_col}")) IN ('TQBR', 'EQBR')
            """

            chunk = pd.read_sql_query(
                sql,
                connection,
                params=batch,
            )

            if not chunk.empty:
                chunks.append(chunk)

            log(
                f"Загружено SECID: "
                f"{min(start + 400, len(unique_secids)):,}"
                f"/{len(unique_secids):,}"
            )

    finally:
        connection.close()

    if not chunks:
        raise RuntimeError("Не удалось загрузить adjusted_daily_bars.")

    bars = pd.concat(chunks, ignore_index=True)

    bars.columns = [str(c).lower() for c in bars.columns]

    bars = bars.rename(
        columns={
            secid_col.lower(): "secid",
            date_col.lower(): "tradedate",
            board_col.lower(): "boardid",
            open_col.lower(): "open",
            close_col.lower(): "close",
        }
    )

    bars["secid"] = normalize_secids(bars["secid"])
    bars["tradedate"] = normalize_dates(bars["tradedate"])
    bars["boardid"] = bars["boardid"].astype(str).str.upper().str.strip()

    bars["open"] = pd.to_numeric(bars["open"], errors="coerce")
    bars["close"] = pd.to_numeric(bars["close"], errors="coerce")

    bars = bars.dropna(
        subset=["secid", "tradedate", "open", "close"]
    )

    bars = bars[
        (bars["open"] > 0)
        & (bars["close"] > 0)
    ].copy()

    bars["board_priority"] = bars["boardid"].map(
        {"TQBR": 0, "EQBR": 1}
    )

    bars = bars.dropna(subset=["board_priority"])

    bars = bars.sort_values(
        ["secid", "tradedate", "board_priority"]
    )

    bars = bars.drop_duplicates(
        subset=["secid", "tradedate"],
        keep="first",
    )

    bars = bars[
        ["secid", "tradedate", "open", "close"]
    ].copy()

    log(f"Валидных агрегированных баров: {len(bars):,}")

    return bars


def build_forward_returns(
    features: pd.DataFrame,
    bars: pd.DataFrame,
    calendar: list[str],
) -> pd.DataFrame:

    log("Расчёт forward returns...")

    calendar_position = {
        date: position
        for position, date in enumerate(calendar)
    }

    base = features.copy()

    base["calendar_position"] = base["tradedate"].map(
        calendar_position
    )

    base = base.dropna(subset=["calendar_position"]).copy()
    base["calendar_position"] = base["calendar_position"].astype(int)

    open_lookup = bars[
        ["secid", "tradedate", "open"]
    ].rename(
        columns={
            "tradedate": "execution_date",
            "open": "execution_open",
        }
    )

    close_lookup = bars[
        ["secid", "tradedate", "close"]
    ].rename(
        columns={
            "tradedate": "exit_date",
            "close": "exit_close",
        }
    )

    for horizon in HORIZONS:
        base["execution_date"] = base["calendar_position"].map(
            lambda p: (
                calendar[p + 1]
                if p + 1 < len(calendar)
                else None
            )
        )

        base["exit_date"] = base["calendar_position"].map(
            lambda p: (
                calendar[p + horizon]
                if p + horizon < len(calendar)
                else None
            )
        )

        temp = base[
            [
                "tradedate",
                "secid",
                "execution_date",
                "exit_date",
            ]
        ].copy()

        temp = temp.merge(
            open_lookup,
            on=["secid", "execution_date"],
            how="left",
        )

        temp = temp.merge(
            close_lookup,
            on=["secid", "exit_date"],
            how="left",
        )

        base[f"forward_return_h{horizon}"] = (
            temp["exit_close"] / temp["execution_open"] - 1.0
        ).to_numpy()

        valid = base[f"forward_return_h{horizon}"].notna().sum()

        log(
            f"H{horizon}: доступных forward returns "
            f"{valid:,}/{len(base):,}"
        )

    base = base.drop(columns=["calendar_position"])

    return base


def residualize(y: np.ndarray, controls: np.ndarray) -> np.ndarray:
    """
    OLS residuals with intercept.
    lstsq устойчив к линейно зависимым контрольным признакам.
    """

    y = np.asarray(y, dtype=float)
    controls = np.asarray(controls, dtype=float)

    design = np.column_stack(
        [np.ones(len(controls)), controls]
    )

    coefficients = np.linalg.lstsq(
        design,
        y,
        rcond=None,
    )[0]

    return y - design @ coefficients


def safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < MIN_CROSS_SECTION:
        return np.nan

    if np.std(a) <= 1e-12 or np.std(b) <= 1e-12:
        return np.nan

    return float(np.corrcoef(a, b)[0, 1])


def calculate_daily_tests(
    data: pd.DataFrame,
) -> pd.DataFrame:

    records = []

    log("Расчёт daily IC и incremental IC...")

    for horizon in HORIZONS:
        target_col = f"forward_return_h{horizon}"

        for date, group in data.groupby("tradedate", sort=True):

            required = FEATURES + [target_col]

            sample = group[required].replace(
                [np.inf, -np.inf],
                np.nan,
            ).dropna()

            n = len(sample)

            if n < MIN_CROSS_SECTION:
                continue

            y = sample[target_col].to_numpy(dtype=float)

            y_rank = (
                sample[target_col]
                .rank(method="average")
                .to_numpy(dtype=float)
            )

            for feature in FEATURES:

                controls = [
                    item for item in FEATURES
                    if item != feature
                ]

                x = sample[feature].to_numpy(dtype=float)

                x_rank = (
                    sample[feature]
                    .rank(method="average")
                    .to_numpy(dtype=float)
                )

                control_values = sample[
                    controls
                ].to_numpy(dtype=float)

                control_ranks = (
                    sample[controls]
                    .rank(method="average")
                    .to_numpy(dtype=float)
                )

                # Обычные IC на той же complete-case выборке.
                raw_ic = safe_corr(x, y)
                raw_rank_ic = safe_corr(x_rank, y_rank)

                # Partial Pearson IC.
                x_residual = residualize(x, control_values)
                y_residual = residualize(y, control_values)

                partial_ic = safe_corr(
                    x_residual,
                    y_residual,
                )

                # Partial Rank IC:
                # сначала ранжируем каждую переменную внутри даты,
                # затем удаляем влияние рангов контрольных признаков.
                x_rank_residual = residualize(
                    x_rank,
                    control_ranks,
                )

                y_rank_residual = residualize(
                    y_rank,
                    control_ranks,
                )

                partial_rank_ic = safe_corr(
                    x_rank_residual,
                    y_rank_residual,
                )

                residual_sd_ratio = (
                    float(np.std(x_residual) / np.std(x))
                    if np.std(x) > 1e-12
                    else np.nan
                )

                records.append(
                    {
                        "tradedate": date,
                        "primitive": feature,
                        "horizon": horizon,
                        "n": n,
                        "raw_ic": raw_ic,
                        "raw_rank_ic": raw_rank_ic,
                        "partial_ic": partial_ic,
                        "partial_rank_ic": partial_rank_ic,
                        "residual_sd_ratio": residual_sd_ratio,
                    }
                )

    result = pd.DataFrame(records)

    if result.empty:
        raise RuntimeError(
            "Daily test не сформировал результатов. "
            "Проверь даты, признаки и forward returns."
        )

    log(f"Получено daily наблюдений: {len(result):,}")

    return result


def hac_test(values: pd.Series, max_lag: int):
    """
    Newey-West HAC test для среднего daily IC.
    Нормальная аппроксимация p-value.
    """

    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy()

    n = len(x)

    if n < 30:
        return np.nan, np.nan

    mean = float(np.mean(x))
    centered = x - mean

    long_run_variance = float(
        np.dot(centered, centered) / n
    )

    lag_limit = min(max_lag, n - 1)

    for lag in range(1, lag_limit + 1):
        gamma = float(
            np.dot(centered[lag:], centered[:-lag]) / n
        )

        weight = 1.0 - lag / (lag_limit + 1.0)

        long_run_variance += 2.0 * weight * gamma

    if long_run_variance <= 0:
        return np.nan, np.nan

    standard_error = math.sqrt(long_run_variance / n)

    if standard_error <= 0:
        return np.nan, np.nan

    t_stat = mean / standard_error
    p_value = math.erfc(abs(t_stat) / math.sqrt(2.0))

    return float(t_stat), float(p_value)


def summarize_group(
    group: pd.DataFrame,
    metric: str,
    horizon: int,
    period: str,
) -> dict:

    values = pd.to_numeric(
        group[metric],
        errors="coerce",
    ).dropna()

    n = len(values)

    if n == 0:
        return {}

    mean = float(values.mean())
    std = float(values.std(ddof=1))

    hac_t, hac_p = hac_test(
        values,
        max_lag=horizon - 1,
    )

    return {
        "period": period,
        "primitive": group["primitive"].iloc[0],
        "horizon": horizon,
        "metric": metric,
        "mean": mean,
        "ir": mean / std if std > 1e-12 else np.nan,
        "positive_share": float((values > 0).mean()),
        "negative_share": float((values < 0).mean()),
        "n_dates": n,
        "hac_t": hac_t,
        "hac_p": hac_p,
    }


def build_summary(daily: pd.DataFrame) -> pd.DataFrame:

    records = []

    metrics = [
        "raw_ic",
        "raw_rank_ic",
        "partial_ic",
        "partial_rank_ic",
    ]

    for (feature, horizon), group in daily.groupby(
        ["primitive", "horizon"],
        sort=True,
    ):

        for metric in metrics:

            records.append(
                summarize_group(
                    group,
                    metric,
                    horizon,
                    "OVERALL",
                )
            )

            for period, (start, end) in PERIODS.items():

                period_group = group[
                    group["tradedate"].between(start, end)
                ]

                if period_group.empty:
                    continue

                records.append(
                    summarize_group(
                        period_group,
                        metric,
                        horizon,
                        period,
                    )
                )

    summary = pd.DataFrame(
        [record for record in records if record]
    )

    return summary


def write_report(
    daily: pd.DataFrame,
    summary: pd.DataFrame,
    data: pd.DataFrame,
) -> None:

    overall = summary[
        summary["period"] == "OVERALL"
    ].copy()

    lines = [
        "# Incremental IC: 8 selected primitives",
        "",
        "## Методология",
        "",
        "Для каждого признака рассчитывается обычный IC, "
        "а также partial IC после удаления линейного влияния "
        "остальных семи признаков.",
        "",
        "Partial Pearson IC рассчитывается по остаткам двух OLS-регрессий: "
        "тестируемого признака и forward return на остальные признаки.",
        "",
        "Partial Rank IC рассчитывается аналогично после ранжирования "
        "переменных внутри каждой даты.",
        "",
        "Все признаки проверяются на одинаковой complete-case выборке "
        "внутри каждой даты. Минимальный размер сечения: "
        f"{MIN_CROSS_SECTION}.",
        "",
        "Forward return: Close[T+H] / Open[T+1] - 1.",
        "",
        "IR здесь равен mean(daily IC) / std(daily IC), "
        "не годовой Sharpe.",
        "",
        "HAC p-value использует Newey-West с лагом H-1 "
        "и нормальную аппроксимацию. P-values не скорректированы "
        "на множественные сравнения.",
        "",
        "## Покрытие",
        "",
        f"- Строк feature frame: {len(data):,}",
        f"- Даты с результатами: {daily['tradedate'].nunique():,}",
        f"- Daily наблюдений: {len(daily):,}",
        f"- Уникальных SECID: {data['secid'].nunique():,}",
        "",
        "## Общие результаты",
        "",
        "| Признак | H | Метрика | Mean | IR | Positive | N dates | HAC p |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]

    for _, row in overall.sort_values(
        ["primitive", "horizon", "metric"]
    ).iterrows():

        lines.append(
            f"| {row['primitive']} "
            f"| {int(row['horizon'])} "
            f"| {row['metric']} "
            f"| {row['mean']:.5f} "
            f"| {row['ir']:.3f} "
            f"| {row['positive_share']:.1%} "
            f"| {int(row['n_dates'])} "
            f"| {row['hac_p']:.4g} |"
        )

    lines += [
        "",
        "## Остаточная вариация признаков",
        "",
        "residual_sd_ratio показывает, какая доля стандартного "
        "отклонения признака остаётся после линейного удаления "
        "остальных семи признаков. Чем меньше значение, тем сильнее "
        "признак объясняется остальным набором.",
        "",
        "| Признак | H | Mean residual SD ratio |",
        "|---|---:|---:|",
    ]

    residual_summary = (
        daily.groupby(["primitive", "horizon"])["residual_sd_ratio"]
        .mean()
        .reset_index()
    )

    for _, row in residual_summary.iterrows():
        lines.append(
            f"| {row['primitive']} "
            f"| {int(row['horizon'])} "
            f"| {row['residual_sd_ratio']:.3f} |"
        )

    lines += [
        "",
        "## Ограничения интерпретации",
        "",
        "- Partial IC выявляет линейную добавочную информацию, "
        "но не исключает нелинейную или режимную ценность.",
        "- Низкий residual_sd_ratio означает сильную избыточность, "
        "но не автоматически бесполезность.",
        "- Дневные наблюдения и forward returns перекрываются во времени. "
        "HAC частично учитывает автокорреляцию, но не устраняет все "
        "проблемы временной зависимости.",
        "- Результаты не являются доказательством доходности стратегии.",
        "- Для окончательного выбора потребуется проверить совместный "
        "сигнал и его устойчивость на отложенных временных отрезках.",
        "",
    ]

    report_path = OUT_DIR / "incremental_ic_report.md"
    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log("Загрузка исходных файлов...")
    panel, features, calendar = load_inputs()

    secids = sorted(features["secid"].unique().tolist())

    bars = load_adjusted_bars(secids)

    data = build_forward_returns(
        features,
        bars,
        calendar,
    )

    daily = calculate_daily_tests(data)

    summary = build_summary(daily)

    daily_path = OUT_DIR / "incremental_ic_daily.csv"
    summary_path = OUT_DIR / "incremental_ic_summary.csv"
    report_path = OUT_DIR / "incremental_ic_report.md"
    metadata_path = OUT_DIR / "metadata.json"

    daily.to_csv(
        daily_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    write_report(daily, summary, data)

    metadata = {
        "features": FEATURES,
        "horizons": HORIZONS,
        "min_cross_section": MIN_CROSS_SECTION,
        "periods": PERIODS,
        "forward_return_definition": "Close[T+H] / Open[T+1] - 1",
        "partial_ic_definition": (
            "Correlation between residuals of feature and forward "
            "return after OLS adjustment for the other seven features."
        ),
        "partial_rank_ic_definition": (
            "Same procedure after within-date rank transformation."
        ),
        "n_feature_rows": int(len(features)),
        "n_target_rows": int(len(data)),
        "n_daily_results": int(len(daily)),
        "n_dates": int(daily["tradedate"].nunique()),
        "n_secids": int(data["secid"].nunique()),
        "outputs": [
            str(daily_path.relative_to(ROOT)),
            str(summary_path.relative_to(ROOT)),
            str(report_path.relative_to(ROOT)),
        ],
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 65)
    print("INCREMENTAL IC TEST COMPLETE")
    print("=" * 65)
    print(f"Daily:   {daily_path}")
    print(f"Summary: {summary_path}")
    print(f"Report:  {report_path}")
    print(f"Metadata:{metadata_path}")


if __name__ == "__main__":
    main()
