
# pipeline/scripts/experiments/primitives/09_core_vs_candidates.py

from pathlib import Path
import json
import sqlite3
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

PANEL_PATH = ROOT / "data/processed/top50/top50_panel.parquet"
FEATURE_PATH = ROOT / "data/interim/primitive_research/primitive_features.parquet"
DB_PATH = ROOT / "data/processed/moex_daily_adjusted.sqlite"

OUT_DIR = ROOT / "data/interim/primitive_research/core_vs_candidates"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TABLE = "adjusted_daily_bars"
HORIZONS = [5, 10, 20]
MIN_NAMES = 20
BATCH_SIZE = 400

CORE = [
    "drawdown_60",
    "zscore_sma20_20",
    "realized_vol_60",
]

CANDIDATES = [
    "drawdown_20",
    "realized_vol_20",
    "return_20",
    "price_sma20",
]

ALL_FEATURES = CORE + CANDIDATES

PERIODS = {
    "2005_2012": ("2005-01-01", "2012-12-31"),
    "2013_2019": ("2013-01-01", "2019-12-31"),
    "2020_2026": ("2020-01-01", "2026-12-31"),
}


def log(message):
    print(message, flush=True)


def normalize_dates(series):
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


def find_column(columns, candidates):
    lookup = {str(c).lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    raise RuntimeError(
        f"Не найдена колонка из {candidates}. "
        f"Доступные колонки: {list(columns)}"
    )


def load_features():
    log("Loading primitive features...")

    df = pd.read_parquet(FEATURE_PATH)

    secid_col = find_column(df.columns, ["secid"])
    date_col = find_column(df.columns, ["tradedate"])

    rename = {
        secid_col: "secid",
        date_col: "tradedate",
    }

    df = df.rename(columns=rename)

    df["secid"] = df["secid"].astype(str).str.strip().str.upper()
    df["tradedate"] = normalize_dates(df["tradedate"])

    required = ["secid", "tradedate"] + ALL_FEATURES
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise RuntimeError(f"В feature frame отсутствуют колонки: {missing}")

    df = df[required].copy()
    df = df.dropna(subset=["secid", "tradedate"])

    duplicated = df.duplicated(["secid", "tradedate"])

    if duplicated.any():
        examples = df.loc[duplicated, ["secid", "tradedate"]].head(10)
        raise RuntimeError(
            "Feature frame содержит дубликаты SECID/TRADEDATE. "
            f"Примеры:\n{examples.to_string(index=False)}"
        )

    for feature in ALL_FEATURES:
        df[feature] = pd.to_numeric(df[feature], errors="coerce")

    log(f"Feature rows: {len(df):,}")
    log(f"Unique SECIDs: {df['secid'].nunique():,}")

    return df


def load_calendar():
    log("Loading panel calendar...")

    panel = pd.read_parquet(PANEL_PATH)

    date_col = find_column(panel.columns, ["tradedate"])
    dates = normalize_dates(panel[date_col]).dropna()

    calendar = sorted(dates.unique().tolist())

    if not calendar:
        raise RuntimeError("Не удалось построить торговый календарь.")

    log(f"Calendar dates: {len(calendar):,}")
    log(f"Calendar range: {calendar[0]} — {calendar[-1]}")

    return calendar


def load_adjusted_bars(secids):
    log("Loading adjusted OHLC from SQLite...")

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

        chunks = []

        secids = sorted(set(secids))

        for start in range(0, len(secids), BATCH_SIZE):
            batch = secids[start:start + BATCH_SIZE]
            placeholders = ",".join(["?"] * len(batch))

            sql = f"""
                SELECT
                    "{secid_col}" AS secid,
                    "{date_col}" AS tradedate,
                    "{board_col}" AS boardid,
                    "{open_col}" AS open,
                    "{close_col}" AS close
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

        if not chunks:
            raise RuntimeError("SQLite не вернула ни одной строки.")

        bars = pd.concat(chunks, ignore_index=True)

    finally:
        connection.close()

    bars["secid"] = bars["secid"].astype(str).str.strip().str.upper()
    bars["tradedate"] = normalize_dates(bars["tradedate"])
    bars["boardid"] = bars["boardid"].astype(str).str.strip().str.upper()

    bars["open"] = pd.to_numeric(bars["open"], errors="coerce")
    bars["close"] = pd.to_numeric(bars["close"], errors="coerce")

    bars = bars.dropna(subset=["secid", "tradedate"])

    # Для forward return используем только положительные Open и Close.
    bars = bars[
        (bars["open"] > 0)
        & (bars["close"] > 0)
    ].copy()

    # TQBR имеет приоритет. EQBR используется как fallback.
    bars["board_priority"] = bars["boardid"].map({
        "TQBR": 0,
        "EQBR": 1,
    })

    bars = bars.sort_values(
        ["secid", "tradedate", "board_priority"]
    )

    bars = bars.drop_duplicates(
        ["secid", "tradedate"],
        keep="first",
    )

    bars = bars[["secid", "tradedate", "open", "close"]].copy()

    if bars.duplicated(["secid", "tradedate"]).any():
        raise RuntimeError("После board selection остались дубликаты.")

    log(f"Selected OHLC rows: {len(bars):,}")
    log(f"Selected SECIDs: {bars['secid'].nunique():,}")

    return bars


def build_forward_returns(features, bars, calendar):
    log("Building forward returns...")

    date_to_position = {
        date: position
        for position, date in enumerate(calendar)
    }

    base = features[["secid", "tradedate"] + ALL_FEATURES].copy()

    base["calendar_position"] = base["tradedate"].map(date_to_position)

    base = base.dropna(subset=["calendar_position"]).copy()
    base["calendar_position"] = base["calendar_position"].astype(int)

    bar_open = bars[["secid", "tradedate", "open"]].rename(
        columns={
            "tradedate": "execution_date",
            "open": "execution_open",
        }
    )

    bar_close = bars[["secid", "tradedate", "close"]].rename(
        columns={
            "tradedate": "exit_date",
            "close": "exit_close",
        }
    )

    result = []

    for horizon in HORIZONS:
        temp = base[
            ["secid", "tradedate", "calendar_position"] + ALL_FEATURES
        ].copy()

        execution_positions = temp["calendar_position"] + 1
        exit_positions = temp["calendar_position"] + horizon

        temp["execution_date"] = execution_positions.map(
            lambda p: calendar[p] if p < len(calendar) else None
        )

        temp["exit_date"] = exit_positions.map(
            lambda p: calendar[p] if p < len(calendar) else None
        )

        temp = temp.dropna(
            subset=["execution_date", "exit_date"]
        )

        temp = temp.merge(
            bar_open,
            on=["secid", "execution_date"],
            how="left",
            validate="many_to_one",
        )

        temp = temp.merge(
            bar_close,
            on=["secid", "exit_date"],
            how="left",
            validate="many_to_one",
        )

        temp[f"forward_return_{horizon}"] = (
            temp["exit_close"] / temp["execution_open"] - 1.0
        )

        temp = temp.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        temp = temp.dropna(
            subset=[
                "execution_open",
                "exit_close",
                f"forward_return_{horizon}",
            ]
        )

        temp["horizon"] = horizon

        result.append(temp)

        log(
            f"H{horizon}: rows with forward return "
            f"{len(temp):,}"
        )

    return pd.concat(result, ignore_index=True)


def safe_corr(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    if len(x) < MIN_NAMES:
        return np.nan

    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan

    return float(np.corrcoef(x, y)[0, 1])


def residualize(y, controls):
    y = np.asarray(y, dtype=float)

    if not controls:
        return y - np.mean(y)

    matrix = np.column_stack([
        np.ones(len(y)),
        *[
            np.asarray(control, dtype=float)
            for control in controls
        ],
    ])

    coefficients, *_ = np.linalg.lstsq(
        matrix,
        y,
        rcond=None,
    )

    return y - matrix @ coefficients


def rank_values(values):
    return pd.Series(values).rank(method="average").to_numpy(dtype=float)


def calculate_daily_metrics(group, feature, controls, target_col):
    required = [feature, target_col] + controls

    sample = group[required].replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    n = len(sample)

    if n < MIN_NAMES:
        return None

    x = sample[feature].to_numpy(dtype=float)
    y = sample[target_col].to_numpy(dtype=float)

    control_values = [
        sample[c].to_numpy(dtype=float)
        for c in controls
    ]

    raw_ic = safe_corr(x, y)

    raw_rank_ic = safe_corr(
        rank_values(x),
        rank_values(y),
    )

    x_residual = residualize(x, control_values)
    y_residual = residualize(y, control_values)

    partial_ic = safe_corr(
        x_residual,
        y_residual,
    )

    ranked_x = rank_values(x)
    ranked_y = rank_values(y)
    ranked_controls = [
        rank_values(c)
        for c in control_values
    ]

    rank_x_residual = residualize(
        ranked_x,
        ranked_controls,
    )

    rank_y_residual = residualize(
        ranked_y,
        ranked_controls,
    )

    partial_rank_ic = safe_corr(
        rank_x_residual,
        rank_y_residual,
    )

    raw_sd = np.std(x, ddof=1)
    residual_sd = np.std(x_residual, ddof=1)

    residual_sd_ratio = (
        residual_sd / raw_sd
        if raw_sd > 0
        else np.nan
    )

    return {
        "n": n,
        "raw_ic": raw_ic,
        "raw_rank_ic": raw_rank_ic,
        "partial_ic": partial_ic,
        "partial_rank_ic": partial_rank_ic,
        "residual_sd_ratio": residual_sd_ratio,
    }


def get_controls(feature):
    if feature in CORE:
        return [c for c in CORE if c != feature]

    return CORE.copy()


def build_daily_results(data):
    log("Calculating daily incremental IC...")

    rows = []

    for horizon in HORIZONS:
        target_col = f"forward_return_{horizon}"

        horizon_data = data[
            data["horizon"] == horizon
        ].copy()

        # Одна complete-case выборка для всех семи признаков.
        # Это обеспечивает сопоставимость результатов.
        common_columns = ALL_FEATURES + [target_col]

        horizon_data = horizon_data.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        horizon_data = horizon_data.dropna(
            subset=common_columns
        )

        log(
            f"H{horizon}: common complete-case rows "
            f"{len(horizon_data):,}"
        )

        for tradedate, group in horizon_data.groupby(
            "tradedate",
            sort=True,
        ):
            if len(group) < MIN_NAMES:
                continue

            for feature in ALL_FEATURES:
                controls = get_controls(feature)

                metrics = calculate_daily_metrics(
                    group,
                    feature,
                    controls,
                    target_col,
                )

                if metrics is None:
                    continue

                rows.append({
                    "tradedate": tradedate,
                    "feature": feature,
                    "role": (
                        "core"
                        if feature in CORE
                        else "candidate"
                    ),
                    "controls": "|".join(controls),
                    "horizon": horizon,
                    **metrics,
                })

    daily = pd.DataFrame(rows)

    if daily.empty:
        raise RuntimeError("Daily results пусты.")

    log(f"Daily observations: {len(daily):,}")

    return daily


def hac_test(values, max_lag):
    x = pd.Series(values).dropna().to_numpy(dtype=float)

    n = len(x)

    if n < 30:
        return np.nan, np.nan

    mean = float(np.mean(x))
    centered = x - mean

    gamma0 = float(np.dot(centered, centered) / n)

    long_run_variance = gamma0

    max_lag = min(max_lag, n - 1)

    for lag in range(1, max_lag + 1):
        gamma = float(
            np.dot(
                centered[lag:],
                centered[:-lag],
            ) / n
        )

        weight = 1.0 - lag / (max_lag + 1)

        long_run_variance += 2.0 * weight * gamma

    variance_mean = long_run_variance / n

    if variance_mean <= 0:
        return np.nan, np.nan

    t_stat = mean / math.sqrt(variance_mean)

    p_value = math.erfc(abs(t_stat) / math.sqrt(2.0))

    return t_stat, p_value


def summarize_group(group):
    horizon = int(group["horizon"].iloc[0])

    result = {
        "feature": group["feature"].iloc[0],
        "role": group["role"].iloc[0],
        "horizon": horizon,
        "period": group["period"].iloc[0],
        "n_dates": len(group),
        "mean_n": group["n"].mean(),
        "median_n": group["n"].median(),
    }

    for metric in [
        "raw_ic",
        "raw_rank_ic",
        "partial_ic",
        "partial_rank_ic",
    ]:
        values = group[metric].dropna()

        mean = values.mean()
        std = values.std(ddof=1)

        result[f"{metric}_mean"] = mean
        result[f"{metric}_ir"] = (
            mean / std
            if std > 0
            else np.nan
        )
        result[f"{metric}_positive_share"] = (
            (values > 0).mean()
            if len(values)
            else np.nan
        )

        _, p_value = hac_test(
            values,
            max_lag=horizon - 1,
        )

        result[f"{metric}_hac_p"] = p_value

    result["residual_sd_ratio_mean"] = (
        group["residual_sd_ratio"].mean()
    )

    return result


def build_summary(daily):
    log("Building summary...")

    daily = daily.copy()
    daily["period"] = "full"

    for period_name, (start, end) in PERIODS.items():
        mask = (
            (daily["tradedate"] >= start)
            & (daily["tradedate"] <= end)
        )

        daily.loc[mask, "period"] = period_name

    rows = []

    for (feature, horizon, period), group in daily.groupby(
        ["feature", "horizon", "period"],
        sort=True,
    ):
        rows.append(summarize_group(group))

    return pd.DataFrame(rows)


def write_report(daily, summary):
    report_path = OUT_DIR / "core_vs_candidates_report.md"

    lines = [
        "# Core vs Additional Candidates",
        "",
        "## Methodology",
        "",
        "Core:",
        "",
    ]

    lines += [f"- `{x}`" for x in CORE]

    lines += [
        "",
        "Additional candidates:",
        "",
    ]

    lines += [f"- `{x}`" for x in CANDIDATES]

    lines += [
        "",
        "Core features are controlled by the other two Core features.",
        "Additional candidates are controlled by all three Core features.",
        "",
        "All seven features use one common complete-case sample per date.",
        "",
        "Forward return: Close[T+H] / Open[T+1] - 1.",
        "",
        "Partial IC is the correlation between residualized feature and",
        "residualized forward return.",
        "",
        "HAC uses Newey-West with lag H-1 and normal approximation.",
        "P-values are not adjusted for multiple comparisons.",
        "",
        "## Coverage",
        "",
        f"- Daily observations: {len(daily):,}",
        f"- Unique dates: {daily['tradedate'].nunique():,}",
        f"- Unique features: {daily['feature'].nunique():,}",
        "",
        "## Summary",
        "",
    ]

    display_columns = [
        "feature",
        "role",
        "horizon",
        "period",
        "n_dates",
        "mean_n",
        "partial_ic_mean",
        "partial_rank_ic_mean",
        "partial_ic_hac_p",
        "partial_rank_ic_hac_p",
        "residual_sd_ratio_mean",
    ]

    table = summary[display_columns].copy()

    lines.append(table.to_markdown(index=False))

    lines += [
        "",
        "## Interpretation",
        "",
        "- Core partial IC tests each Core feature beyond the other two.",
        "- Candidate partial IC tests each candidate beyond the retained Core.",
        "- A weak candidate result does not prove absence of nonlinear value.",
        "- Realized_vol_60 is retained as a risk descriptor; this experiment",
        "  does not test its ability to forecast future realized volatility",
        "  or drawdown.",
        "- Results are not evidence of a profitable strategy.",
        "",
    ]

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    log(f"Report saved: {report_path}")


def main():
    log("=" * 70)
    log("CORE VS CANDIDATES")
    log("=" * 70)

    features = load_features()
    calendar = load_calendar()

    bars = load_adjusted_bars(
        features["secid"].unique().tolist()
    )

    forward = build_forward_returns(
        features,
        bars,
        calendar,
    )

    daily = build_daily_results(forward)
    summary = build_summary(daily)

    daily_path = OUT_DIR / "core_vs_candidates_daily.csv"
    summary_path = OUT_DIR / "core_vs_candidates_summary.csv"
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

    metadata = {
        "core": CORE,
        "candidates": CANDIDATES,
        "horizons": HORIZONS,
        "min_names": MIN_NAMES,
        "daily_rows": int(len(daily)),
        "unique_dates": int(daily["tradedate"].nunique()),
        "unique_secids": int(features["secid"].nunique()),
        "common_complete_case_features": ALL_FEATURES,
        "method": (
            "Cross-sectional partial IC. Core features controlled "
            "by other Core features; candidates controlled by all Core."
        ),
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    write_report(daily, summary)

    log("=" * 70)
    log("EXPERIMENT 09 COMPLETE")
    log("=" * 70)
    log(f"Daily: {daily_path}")
    log(f"Summary: {summary_path}")
    log(f"Report: {OUT_DIR / 'core_vs_candidates_report.md'}")
    log(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
