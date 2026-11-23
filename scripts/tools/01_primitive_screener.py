# Folder: scripts/tools/
# File: 01_primitive_screener.py
# Purpose: Print the current PIT TOP50 instrument-state snapshot from
#          the three approved core primitives and save it as one CSV.
#
# Inputs:
#   data/processed/top50/top50_panel.parquet
#   data/interim/primitive_research/primitive_features.parquet
#
# Output:
#   data/interim/screener/latest_primitive_snapshot.csv
#   data/interim/screener/latest_market_breadth.csv
#
# Run:
#   python scripts/tools/01_primitive_screener.py
#   python scripts/tools/01_primitive_screener.py --inspect

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PANEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "top50"
    / "top50_panel.parquet"
)

FEATURE_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "primitive_research"
    / "primitive_features.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "screener"
    / "latest_primitive_snapshot.csv"
)

BREADTH_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "screener"
    / "latest_market_breadth.csv"
)

TOP_N = 15

PRIMITIVES = {
    "drawdown_60": {
        "label": "Близость к максимуму за 60 сессий",
        "description": "Чем выше значение, тем ближе цена к 60-сессионному максимуму.",
        "format": "percent",
    },
    "zscore_sma20_20": {
        "label": "Отклонение от SMA20",
        "description": "Положительное значение означает цену выше SMA20.",
        "format": "number",
    },
    "realized_vol_60": {
        "label": "Реализованная волатильность за 60 сессий",
        "description": "Годовая оценка исторической волатильности.",
        "format": "percent",
    },
}


# ============================================================
# HELPERS
# ============================================================

def log(message: str) -> None:
    print(message, flush=True)


def resolve_column(
    frame: pd.DataFrame,
    expected: str,
) -> str:
    lookup = {
        str(column).strip().lower(): column
        for column in frame.columns
    }

    actual = lookup.get(expected.lower())

    if actual is None:
        raise RuntimeError(
            f"Не найдена колонка '{expected}'. "
            f"Доступные колонки: {list(frame.columns)}"
        )

    return actual


def normalize_secid(series: pd.Series) -> pd.Series:
    return (
        series
        .astype(str)
        .str.strip()
        .str.upper()
    )


def normalize_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series,
        errors="coerce",
    ).dt.normalize()


def format_value(
    value: object,
    value_format: str,
) -> str:
    if pd.isna(value):
        return "N/A"

    number = float(value)

    if value_format == "percent":
        return f"{number:+.2%}"

    return f"{number:+.3f}"


def atomic_write_csv(
    frame: pd.DataFrame,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        destination.stem + ".tmp" + destination.suffix
    )

    frame.to_csv(
        temporary,
        index=False,
        encoding="utf-8-sig",
        float_format="%.10g",
    )

    temporary.replace(destination)


# ============================================================
# LOAD CURRENT PIT TOP50
# ============================================================

def load_latest_panel() -> tuple[pd.DataFrame, pd.Timestamp]:
    if not PANEL_PATH.is_file():
        raise FileNotFoundError(
            f"TOP50 panel не найден: {PANEL_PATH}"
        )

    panel = pd.read_parquet(PANEL_PATH)

    date_column = resolve_column(panel, "tradedate")
    secid_column = resolve_column(panel, "secid")
    rank_column = resolve_column(panel, "rank")
    bar_column = resolve_column(panel, "bar_available")

    selected = panel[
        [
            date_column,
            secid_column,
            rank_column,
            bar_column,
        ]
    ].copy()

    selected.columns = [
        "tradedate",
        "secid",
        "panel_rank",
        "bar_available",
    ]

    selected["tradedate"] = normalize_date(
        selected["tradedate"]
    )
    selected["secid"] = normalize_secid(
        selected["secid"]
    )
    selected["panel_rank"] = pd.to_numeric(
        selected["panel_rank"],
        errors="coerce",
    )
    selected["bar_available"] = pd.to_numeric(
        selected["bar_available"],
        errors="coerce",
    ).fillna(0).astype(int)

    selected = selected.dropna(
        subset=["tradedate", "secid"]
    ).copy()

    if selected.empty:
        raise RuntimeError(
            "TOP50 panel не содержит валидных строк."
        )

    snapshot_date = selected["tradedate"].max()

    latest = selected[
        selected["tradedate"].eq(snapshot_date)
    ].copy()

    if latest["secid"].duplicated().any():
        duplicates = latest.loc[
            latest["secid"].duplicated(keep=False),
            "secid",
        ].tolist()

        raise RuntimeError(
            "Дубликаты SECID в последнем PIT TOP50 срезе: "
            f"{duplicates}"
        )

    latest = latest.sort_values(
        ["panel_rank", "secid"],
        kind="mergesort",
    ).reset_index(drop=True)

    if len(latest) != 50:
        log(
            f"WARNING: в последнем срезе {len(latest)} тикеров, "
            "ожидалось 50. Отчет будет построен по фактическому составу."
        )

    return latest, snapshot_date


# ============================================================
# LOAD CURRENT PRIMITIVE VALUES
# ============================================================

def load_features(
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    if not FEATURE_PATH.is_file():
        raise FileNotFoundError(
            f"Primitive feature frame не найден: {FEATURE_PATH}\n"
            "Сначала запусти "
            "scripts/experiments/primitives/05_build_primitive_features.py"
        )

    features = pd.read_parquet(FEATURE_PATH)

    required = [
        "tradedate",
        "secid",
        *PRIMITIVES.keys(),
    ]

    actual_columns = {
        name: resolve_column(features, name)
        for name in required
    }

    features = features[
        [actual_columns[name] for name in required]
    ].copy()

    features.columns = required

    features["tradedate"] = normalize_date(
        features["tradedate"]
    )
    features["secid"] = normalize_secid(
        features["secid"]
    )

    for primitive in PRIMITIVES:
        features[primitive] = pd.to_numeric(
            features[primitive],
            errors="coerce",
        )

    features = features.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    features = features.dropna(
        subset=["tradedate", "secid"]
    ).copy()

    if features.duplicated(
        ["tradedate", "secid"]
    ).any():
        raise RuntimeError(
            "Дубликаты SECID/TRADEDATE в primitive_features.parquet."
        )

    latest_feature_date = features["tradedate"].max()

    if pd.isna(latest_feature_date):
        raise RuntimeError(
            "В primitive_features.parquet нет валидных дат."
        )

    if latest_feature_date < snapshot_date:
        raise RuntimeError(
            "Primitive feature frame устарел.\n"
            f"Последняя дата панели: {snapshot_date:%Y-%m-%d}\n"
            f"Последняя дата features: {latest_feature_date:%Y-%m-%d}\n"
            "Пересобери features командой:\n"
            "python scripts/experiments/primitives/05_build_primitive_features.py"
        )

    current = features[
        features["tradedate"].eq(snapshot_date)
    ].copy()

    return current



# ============================================================
# LOAD HISTORICAL MARKET BREADTH
# ============================================================

def load_market_breadth(snapshot_date: pd.Timestamp) -> pd.DataFrame:
    """Reproduce the approved PIT breadth definitions from research."""
    panel = pd.read_parquet(PANEL_PATH)
    features = pd.read_parquet(FEATURE_PATH)

    ph = panel[
        [resolve_column(panel, "tradedate"),
         resolve_column(panel, "secid"),
         resolve_column(panel, "bar_available")]
    ].copy()
    ph.columns = ["tradedate", "secid", "bar_available"]

    fh = features[
        [resolve_column(features, "tradedate"),
         resolve_column(features, "secid"),
         resolve_column(features, "price_sma20")]
    ].copy()
    fh.columns = ["tradedate", "secid", "price_sma20"]

    ph["tradedate"] = normalize_date(ph["tradedate"])
    ph["secid"] = normalize_secid(ph["secid"])
    ph["bar_available"] = pd.to_numeric(
        ph["bar_available"], errors="coerce"
    ).fillna(0).astype(int)
    fh["tradedate"] = normalize_date(fh["tradedate"])
    fh["secid"] = normalize_secid(fh["secid"])
    fh["price_sma20"] = pd.to_numeric(
        fh["price_sma20"], errors="coerce"
    ).replace([np.inf, -np.inf], np.nan)

    ph = ph.dropna(subset=["tradedate", "secid"])
    fh = fh.dropna(subset=["tradedate", "secid"])

    if ph.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Дубликаты SECID/TRADEDATE в исторической TOP50 panel.")
    if fh.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Дубликаты SECID/TRADEDATE в primitive feature frame.")

    history = ph.merge(
        fh, on=["tradedate", "secid"], how="left", validate="one_to_one"
    )
    # Exactly as in research: actual bars only; missing bars are not negatives.
    history = history[history["bar_available"].eq(1)].copy()

    calendar = pd.DatetimeIndex(sorted(ph["tradedate"].unique()))
    valid = history.dropna(subset=["price_sma20"])

    if valid.empty:
        daily = pd.DataFrame(
            index=calendar,
            columns=["breadth_sma20", "breadth_sma20_valid_n"],
        )
    else:
        daily = valid.groupby("tradedate")["price_sma20"].agg(
            breadth_sma20=lambda values: float((values > 0).mean()),
            breadth_sma20_valid_n="count",
        ).reindex(calendar)

    daily["breadth_sma20"] = pd.to_numeric(
        daily["breadth_sma20"], errors="coerce"
    )
    daily["breadth_change_5"] = daily["breadth_sma20"].diff(5)
    if snapshot_date not in daily.index:
        raise RuntimeError(
            f"Дата {snapshot_date:%Y-%m-%d} отсутствует в календаре breadth."
        )

    pos = daily.index.get_loc(snapshot_date)
    lag_date = daily.index[pos - 5] if pos >= 5 else pd.NaT
    daily.index.name = "snapshot_date"
    current = daily.loc[[snapshot_date]].reset_index()
    current["snapshot_date"] = current["snapshot_date"].dt.strftime("%Y-%m-%d")
    current["breadth_sma20_universe_n"] = int(
        ph.loc[ph["tradedate"].eq(snapshot_date), "secid"].nunique()
    )
    current["breadth_change_5_base_date"] = (
        lag_date.strftime("%Y-%m-%d") if pd.notna(lag_date) else ""
    )
    return current[
        ["snapshot_date", "breadth_sma20", "breadth_sma20_valid_n",
         "breadth_sma20_universe_n", "breadth_change_5",
         "breadth_change_5_base_date"]
    ]


# ============================================================
# BUILD SNAPSHOT
# ============================================================

def build_snapshot(
    panel: pd.DataFrame,
    features: pd.DataFrame,
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    snapshot = panel.merge(
        features.drop(columns=["tradedate"]),
        on="secid",
        how="left",
        validate="one_to_one",
    )

    snapshot.insert(
        0,
        "snapshot_date",
        snapshot_date.strftime("%Y-%m-%d"),
    )

    primitive_columns = list(PRIMITIVES)

    snapshot["instrument_status"] = np.select(
        [
            snapshot["bar_available"].eq(0),
            snapshot[primitive_columns].notna().all(axis=1),
        ],
        [
            "NO_BAR",
            "OK",
        ],
        default="FEATURES_INCOMPLETE",
    )

    missing_by_row = snapshot[primitive_columns].isna()

    snapshot["missing_primitives"] = missing_by_row.apply(
        lambda row: "|".join(
            row.index[row].tolist()
        ),
        axis=1,
    )

    for primitive in PRIMITIVES:
        rank_column = f"{primitive}_rank"
        percentile_column = f"{primitive}_percentile"

        valid = snapshot[primitive].notna()

        snapshot[rank_column] = np.nan
        snapshot[percentile_column] = np.nan

        if valid.any():
            values = snapshot.loc[valid, primitive]

            snapshot.loc[valid, rank_column] = (
                values.rank(
                    ascending=False,
                    method="min",
                )
            )

            snapshot.loc[valid, percentile_column] = (
                values.rank(
                    ascending=True,
                    method="average",
                    pct=True,
                ) * 100.0
            )

    ordered_columns = [
        "snapshot_date",
        "secid",
        "panel_rank",
        "bar_available",
        "instrument_status",
        "missing_primitives",
    ]

    for primitive in PRIMITIVES:
        ordered_columns.extend([
            primitive,
            f"{primitive}_rank",
            f"{primitive}_percentile",
        ])

    return snapshot[ordered_columns].sort_values(
        ["panel_rank", "secid"],
        kind="mergesort",
    ).reset_index(drop=True)


# ============================================================
# CONSOLE REPORT
# ============================================================


def print_market_breadth(breadth: pd.DataFrame) -> None:
    row = breadth.iloc[0]
    level = f"{row['breadth_sma20']:.2%}" if pd.notna(row["breadth_sma20"]) else "N/A"
    change = f"{row['breadth_change_5'] * 100:+.2f} п.п." if pd.notna(row["breadth_change_5"]) else "N/A"
    n = int(row["breadth_sma20_valid_n"]) if pd.notna(row["breadth_sma20_valid_n"]) else 0
    total = int(row["breadth_sma20_universe_n"])
    print()
    print("=" * 88)
    print("MARKET BREADTH")
    print("=" * 88)
    print(f"breadth_change_5: {change} (5 торговых сессий; база: {row['breadth_change_5_base_date'] or 'N/A'})")
    print(f"breadth_sma20:    {level} (справочно; валидно: {n}/{total})")
    print("=" * 88)


def print_top_15(snapshot: pd.DataFrame) -> None:
    print()
    print("=" * 88)
    print(
        f"PRIMITIVE SCREENER | "
        f"{snapshot['snapshot_date'].iloc[0]} | "
        f"{len(snapshot)} tickers"
    )
    print("=" * 88)

    for primitive, metadata in PRIMITIVES.items():
        valid = snapshot.dropna(
            subset=[primitive]
        ).sort_values(
            [primitive, "secid"],
            ascending=[
                primitive == "realized_vol_60",
                True,
            ],
            kind="mergesort",
        ).head(TOP_N)

        print()
        print("-" * 88)
        print(
            f"{primitive} | {metadata['label']} "
            f"| valid: {snapshot[primitive].notna().sum()}/{len(snapshot)}"
        )
        print(metadata["description"])
        print("-" * 88)
        print(
            f"{'RANK':>4}  {'SECID':<16} "
            f"{'VALUE':>14}  {'PANEL':>6}  {'STATUS'}"
        )

        if valid.empty:
            print("Нет валидных значений.")
            continue

        for display_rank, (_, row) in enumerate(
            valid.iterrows(),
            start=1,
        ):
            value = format_value(
                row[primitive],
                metadata["format"],
            )

            panel_rank = (
                str(int(row["panel_rank"]))
                if pd.notna(row["panel_rank"])
                else "N/A"
            )

            print(
                f"{display_rank:>4}  "
                f"{row['secid']:<16} "
                f"{value:>14}  "
                f"{panel_rank:>6}  "
                f"{row['instrument_status']}"
            )

    print()
    print("=" * 88)


# ============================================================
# OPTIONAL TICKER INSPECTION
# ============================================================

def inspect_tickers(snapshot: pd.DataFrame) -> None:
    print()
    raw = input(
        "Введи SECID через пробел (например: SBER DOMRF): "
    ).strip()

    tickers = list(dict.fromkeys(
        token.upper()
        for token in raw.split()
    ))

    if not tickers:
        print("Тикеры не введены.")
        return

    indexed = snapshot.set_index(
        "secid",
        drop=False,
    )

    for ticker in tickers:
        print()
        print("-" * 72)
        print(f"SECID: {ticker}")

        if ticker not in indexed.index:
            print("Не входит в последний PIT TOP50 срез.")
            continue

        row = indexed.loc[ticker]

        print(f"Дата среза:       {row['snapshot_date']}")
        print(f"Место в TOP50:    {int(row['panel_rank']) if pd.notna(row['panel_rank']) else 'N/A'}")
        print(f"Бар на дату:      {'есть' if int(row['bar_available']) == 1 else 'нет'}")
        print(f"Статус:           {row['instrument_status']}")

        for primitive, metadata in PRIMITIVES.items():
            value = format_value(
                row[primitive],
                metadata["format"],
            )

            rank = (
                str(int(row[f"{primitive}_rank"]))
                if pd.notna(row[f"{primitive}_rank"])
                else "N/A"
            )

            percentile = (
                f"{row[f'{primitive}_percentile']:.1f}"
                if pd.notna(row[f"{primitive}_percentile"])
                else "N/A"
            )

            print(
                f"{primitive:<22} "
                f"value={value:>10}  "
                f"rank={rank:>3}  "
                f"percentile={percentile:>5}"
            )

        if row["missing_primitives"]:
            print(
                "Нет значений: "
                f"{row['missing_primitives']}"
            )

    print()
    print("-" * 72)


# ============================================================
# MAIN
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Текущий PIT TOP50 срез по трем core-примитивам. "
            "Не является торговой стратегией."
        )
    )

    parser.add_argument(
        "--inspect",
        action="store_true",
        help=(
            "После основного отчета запросить SECID через пробел "
            "и вывести индивидуальную информацию по тикерам."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        log("Loading latest PIT TOP50 panel...")
        panel, snapshot_date = load_latest_panel()

        log(
            f"Latest panel date: {snapshot_date:%Y-%m-%d}; "
            f"tickers: {len(panel)}"
        )

        log("Loading primitive feature values...")
        features = load_features(snapshot_date)

        log(
            f"Feature rows on snapshot date: {len(features)}"
        )

        snapshot = build_snapshot(
            panel,
            features,
            snapshot_date,
        )
        breadth = load_market_breadth(snapshot_date)

        atomic_write_csv(snapshot, OUTPUT_PATH)
        atomic_write_csv(breadth, BREADTH_OUTPUT_PATH)

        log(f"CSV saved: {OUTPUT_PATH}")
        log(f"Market breadth CSV saved: {BREADTH_OUTPUT_PATH}")

        print_market_breadth(breadth)
        print_top_15(snapshot)

        if args.inspect:
            inspect_tickers(snapshot)

        return 0

    except Exception as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
