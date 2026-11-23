
# Folder: scripts/experiments/primitives/
# File: 05_build_primitive_features.py
# Purpose: Build and save the PIT TOP50 cross-sectional primitive feature frame.
#
# Input:
#   data/processed/top50/top50_panel.parquet
#   data/processed/moex_daily_adjusted.sqlite (read-only)
#
# Output:
#   data/interim/primitive_research/primitive_features.parquet
#   data/interim/primitive_research/primitive_features_metadata.json
#   data/interim/primitive_research/primitive_features_quality.csv
#
# Execution:
#   python scripts/experiments/primitives/05_build_primitive_features.py
#
# Methodology:
#   Feature formulas and data handling are aligned with
#   01_research_report.py. No forward returns, IC, or breadth are calculated.

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PANEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "top50"
    / "top50_panel.parquet"
)

ADJUSTED_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "moex_daily_adjusted.sqlite"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "primitive_research"
)

OUTPUT_PATH = OUTPUT_DIR / "primitive_features.parquet"
METADATA_PATH = OUTPUT_DIR / "primitive_features_metadata.json"
QUALITY_PATH = OUTPUT_DIR / "primitive_features_quality.csv"

TABLE_NAME = "adjusted_daily_bars"

APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}

EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}

SUSPENSION_START = "2022-02-28"
SUSPENSION_END = "2022-03-23"

CHUNK_SIZE = 400

CROSS_SECTIONAL_FEATURES = [
    "price_sma20",
    "sma20_sma50",
    "sma50_sma200",
    "return_5",
    "return_20",
    "return_60",
    "realized_vol_20",
    "realized_vol_60",
    "drawdown_20",
    "drawdown_60",
    "turnover_ratio_20",
    "rs_rank_20",
    "rs_rank_60",
    "rebound_20",
    "rebound_60",
    "zscore_sma20_20",
    "momentum_acceleration_20",
    "efficiency_ratio_20",
    "up_down_turnover_ratio_20",
    "positive_turnover_share_20",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"

    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")

    return connection


def atomic_write_parquet(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    temporary = destination.with_name(
        destination.stem + ".tmp" + destination.suffix
    )

    dataframe.to_parquet(
        temporary,
        index=False,
        compression="zstd",
    )

    temporary.replace(destination)


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    temporary.replace(path)


def validate_inputs() -> None:
    if not PANEL_PATH.is_file():
        raise FileNotFoundError(
            f"TOP50 panel not found: {PANEL_PATH}"
        )

    if not ADJUSTED_DB_PATH.is_file():
        raise FileNotFoundError(
            f"Adjusted SQLite database not found: {ADJUSTED_DB_PATH}"
        )


# ============================================================
# LOAD POINT-IN-TIME TOP50 MEMBERSHIP
# ============================================================

def load_panel() -> pd.DataFrame:
    log(f"Reading TOP50 panel: {PANEL_PATH}")

    panel = pd.read_parquet(PANEL_PATH)

    required = {
        "tradedate",
        "secid",
        "rank",
        "universe_size",
        "bar_available",
    }

    missing = required - set(panel.columns)

    if missing:
        raise RuntimeError(
            f"TOP50 panel is missing columns: {sorted(missing)}"
        )

    panel["tradedate"] = pd.to_datetime(
        panel["tradedate"],
        errors="coerce",
    )

    panel["secid"] = (
        panel["secid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    panel = panel.dropna(
        subset=["tradedate", "secid"]
    ).copy()

    panel = panel[
        ~panel["secid"].isin(EXCLUDED_TICKERS)
    ].copy()

    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError(
            "Duplicate tradedate/SECID rows in TOP50 panel."
        )

    panel["bar_available"] = pd.to_numeric(
        panel["bar_available"],
        errors="coerce",
    ).fillna(0).astype(int)

    panel["rank"] = pd.to_numeric(
        panel["rank"],
        errors="coerce",
    )

    panel["universe_size"] = pd.to_numeric(
        panel["universe_size"],
        errors="coerce",
    )

    log(
        f"Panel rows: {len(panel):,}; "
        f"dates: {panel['tradedate'].nunique():,}; "
        f"tickers: {panel['secid'].nunique():,}"
    )

    return panel


# ============================================================
# LOAD ADJUSTED HISTORY
# ============================================================

def load_market_calendar(
    connection: sqlite3.Connection,
) -> pd.DatetimeIndex:
    placeholders = ",".join(
        "?" for _ in APPROVED_BOARDS
    )

    query = f"""
        SELECT DISTINCT tradedate
        FROM "{TABLE_NAME}"
        WHERE boardid IN ({placeholders})
          AND tradedate IS NOT NULL
        ORDER BY tradedate
    """

    dates = pd.read_sql_query(
        query,
        connection,
        params=list(APPROVED_BOARDS),
    )

    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            dates["tradedate"],
            errors="coerce",
        )
    )

    calendar = (
        calendar
        .dropna()
        .unique()
        .sort_values()
    )

    calendar = calendar[
        (calendar < pd.Timestamp(SUSPENSION_START))
        | (calendar > pd.Timestamp(SUSPENSION_END))
    ]

    return calendar



def load_adjusted_history(
    secids: list[str],
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    log("Opening adjusted SQLite in read-only mode...")

    chunks = []

    board_placeholders = ",".join(
        "?" for _ in APPROVED_BOARDS
    )

    with readonly_connection(ADJUSTED_DB_PATH) as connection:
        calendar = load_market_calendar(connection)

        for start in range(0, len(secids), CHUNK_SIZE):
            batch = secids[start:start + CHUNK_SIZE]

            ticker_placeholders = ",".join(
                "?" for _ in batch
            )

            query = f"""
                SELECT
                    UPPER(TRIM(secid)) AS secid,
                    tradedate,
                    boardid,
                    adjusted_open,
                    adjusted_high,
                    adjusted_low,
                    adjusted_close,
                    adjusted_volume,
                    value
                FROM "{TABLE_NAME}"
                WHERE boardid IN ({board_placeholders})
                  AND UPPER(TRIM(secid)) IN ({ticker_placeholders})
                  AND tradedate IS NOT NULL
                ORDER BY tradedate, secid, boardid
            """

            frame = pd.read_sql_query(
                query,
                connection,
                params=[
                    *APPROVED_BOARDS,
                    *batch,
                ],
            )

            if not frame.empty:
                chunks.append(frame)

            completed = min(
                start + CHUNK_SIZE,
                len(secids),
            )

            log(
                f"Loaded ticker history: "
                f"{completed:,}/{len(secids):,}"
            )

    if not chunks:
        raise RuntimeError(
            "No adjusted daily bars found for TOP50 tickers."
        )

    source = pd.concat(
        chunks,
        ignore_index=True,
    )

    source["secid"] = (
        source["secid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    source["boardid"] = (
        source["boardid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    source["tradedate"] = pd.to_datetime(
        source["tradedate"],
        errors="coerce",
    )

    source = source.dropna(
        subset=["secid", "tradedate"]
    ).copy()

    source = source[
        ~source["secid"].isin(EXCLUDED_TICKERS)
    ].copy()

    source = source[
        (source["tradedate"] < pd.Timestamp(SUSPENSION_START))
        | (source["tradedate"] > pd.Timestamp(SUSPENSION_END))
    ].copy()

    numeric_columns = [
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
        "adjusted_volume",
        "value",
    ]

    for column in numeric_columns:
        source[column] = pd.to_numeric(
            source[column],
            errors="coerce",
        )

    if source.duplicated(
        ["secid", "tradedate", "boardid"]
    ).any():
        raise RuntimeError(
            "Duplicate SECID/TRADEDATE/BOARDID rows "
            "in adjusted history."
        )

    source["value"] = source["value"].fillna(0.0)

    source["adjusted_volume"] = (
        source["adjusted_volume"].fillna(0.0)
    )

    activity = (
        source.groupby(
            ["secid", "tradedate"],
            as_index=False,
        )
        .agg(
            value=("value", "sum"),
            adjusted_volume=("adjusted_volume", "sum"),
        )
    )

    price_fields = [
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
    ]

    source["_valid_ohlc"] = (
        source[price_fields]
        .notna()
        .all(axis=1)
        .astype("int8")
    )

    source["_board_priority"] = (
        source["boardid"]
        .map(PRICE_BOARD_PRIORITY)
        .fillna(999)
    )

    prices = (
        source.sort_values(
            [
                "secid",
                "tradedate",
                "_valid_ohlc",
                "_board_priority",
                "boardid",
            ],
            ascending=[
                True,
                True,
                False,
                True,
                True,
            ],
            kind="mergesort",
        )
        .drop_duplicates(
            ["secid", "tradedate"],
            keep="first",
        )
    )

    prices = prices[
        [
            "secid",
            "tradedate",
            "adjusted_open",
            "adjusted_high",
            "adjusted_low",
            "adjusted_close",
            "boardid",
        ]
    ].rename(
        columns={"boardid": "price_board"}
    )

    history = activity.merge(
        prices,
        on=["secid", "tradedate"],
        how="left",
        validate="one_to_one",
    )

    history = history.sort_values(
        ["secid", "tradedate"]
    ).reset_index(drop=True)

    log(
        f"Aggregated history rows: {len(history):,}; "
        f"tickers: {history['secid'].nunique():,}; "
        f"market sessions: {len(calendar):,}"
    )

    return history, calendar



# ============================================================
# CALCULATE PER-TICKER PRIMITIVES
# ============================================================

def build_ticker_features(
    ticker_history: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    ticker = ticker_history["secid"].iloc[0]

    indexed = (
        ticker_history
        .set_index("tradedate")
        .reindex(calendar)
    )

    close = pd.to_numeric(
        indexed["adjusted_close"],
        errors="coerce",
    )

    turnover = pd.to_numeric(
        indexed["value"],
        errors="coerce",
    )

    # After first observed bar, missing ticker/session turnover is zero.
    # Before first observed bar, turnover history remains unknown.
    first_observed = ticker_history["tradedate"].min()

    turnover = turnover.fillna(0.0)
    turnover.loc[
        turnover.index < first_observed
    ] = np.nan

    daily_return = close.pct_change(
        fill_method=None
    )

    sma20 = close.rolling(
        20,
        min_periods=20,
    ).mean()

    sma50 = close.rolling(
        50,
        min_periods=50,
    ).mean()

    sma200 = close.rolling(
        200,
        min_periods=200,
    ).mean()

    residual20 = close - sma20

    residual_std20 = residual20.rolling(
        20,
        min_periods=20,
    ).std(ddof=1)

    features = pd.DataFrame(index=calendar)
    features["secid"] = ticker

    # Price relative to moving averages.
    features["price_sma20"] = (
        close / sma20 - 1.0
    )

    features["sma20_sma50"] = (
        sma20 / sma50 - 1.0
    )

    features["sma50_sma200"] = (
        sma50 / sma200 - 1.0
    )

    # Price momentum.
    features["return_5"] = (
        close / close.shift(5) - 1.0
    )

    features["return_20"] = (
        close / close.shift(20) - 1.0
    )

    features["return_60"] = (
        close / close.shift(60) - 1.0
    )

    # Annualized realized volatility.
    features["realized_vol_20"] = (
        daily_return
        .rolling(20, min_periods=20)
        .std(ddof=1)
        * math.sqrt(252)
    )

    features["realized_vol_60"] = (
        daily_return
        .rolling(60, min_periods=60)
        .std(ddof=1)
        * math.sqrt(252)
    )

    # Distance from rolling highs.
    features["drawdown_20"] = (
        close / close.rolling(
            20,
            min_periods=20,
        ).max() - 1.0
    )

    features["drawdown_60"] = (
        close / close.rolling(
            60,
            min_periods=60,
        ).max() - 1.0
    )

    # Turnover relative to its 20-session mean.
    mean_turnover20 = turnover.rolling(
        20,
        min_periods=20,
    ).mean()

    features["turnover_ratio_20"] = (
        turnover / mean_turnover20
    )

    # Rebound from rolling lows.
    features["rebound_20"] = (
        close / close.rolling(
            20,
            min_periods=20,
        ).min() - 1.0
    )

    features["rebound_60"] = (
        close / close.rolling(
            60,
            min_periods=60,
        ).min() - 1.0
    )

    # Distance from SMA20 in rolling residual standard deviations.
    features["zscore_sma20_20"] = (
        residual20 / residual_std20
    )

    # Change in 20-session momentum over five sessions.
    return20 = features["return_20"]

    features["momentum_acceleration_20"] = (
        return20 - return20.shift(5)
    )

    # Absolute net move divided by total absolute path length.
    net_move20 = (
        close - close.shift(20)
    ).abs()

    path_length20 = (
        close.diff()
        .abs()
        .rolling(20, min_periods=20)
        .sum()
    )

    features["efficiency_ratio_20"] = (
        net_move20 / path_length20
    )

    # Turnover on positive and negative return days.
    up_mask = daily_return > 0
    down_mask = daily_return < 0

    up_turnover = turnover.where(
        up_mask,
        0.0,
    )

    down_turnover = turnover.where(
        down_mask,
        0.0,
    )

    up_count = (
        up_mask.astype(float)
        .rolling(20, min_periods=20)
        .sum()
    )

    down_count = (
        down_mask.astype(float)
        .rolling(20, min_periods=20)
        .sum()
    )

    mean_up_turnover = (
        up_turnover.rolling(
            20,
            min_periods=20,
        ).sum()
        / up_count.replace(0, np.nan)
    )

    mean_down_turnover = (
        down_turnover.rolling(
            20,
            min_periods=20,
        ).sum()
        / down_count.replace(0, np.nan)
    )

    features["up_down_turnover_ratio_20"] = (
        mean_up_turnover / mean_down_turnover
    )

    total_turnover20 = turnover.rolling(
        20,
        min_periods=20,
    ).sum()

    features["positive_turnover_share_20"] = (
        up_turnover.rolling(
            20,
            min_periods=20,
        ).sum()
        / total_turnover20.replace(0, np.nan)
    )

    return (
        features
        .rename_axis("tradedate")
        .reset_index()
    )


# ============================================================
# BUILD PIT TOP50 FEATURE FRAME
# ============================================================

def build_feature_frame(
    panel: pd.DataFrame,
    history: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    log("Preparing signal-date PIT TOP50 membership...")

    membership = panel[
        [
            "tradedate",
            "secid",
            "rank",
            "universe_size",
            "bar_available",
        ]
    ].copy()

    # Match the original research report:
    # only signal-date rows with an actual current bar are evaluated.
    membership = membership[
        membership["bar_available"].eq(1)
    ].copy()

    if membership.empty:
        raise RuntimeError(
            "No PIT TOP50 rows with bar_available=1."
        )

    history_groups = {
        ticker: group
        for ticker, group in history.groupby(
            "secid",
            sort=False,
        )
    }

    selected_tickers = sorted(
        membership["secid"].unique()
    )

    ticker_dates = {
        ticker: group["tradedate"].to_numpy()
        for ticker, group in membership.groupby(
            "secid",
            sort=False,
        )
    }

    chunks = []

    log(
        f"Calculating features for "
        f"{len(selected_tickers):,} PIT TOP50 tickers..."
    )

    for number, ticker in enumerate(
        selected_tickers,
        start=1,
    ):
        ticker_history = history_groups.get(ticker)

        if ticker_history is None:
            raise RuntimeError(
                f"No adjusted history found for PIT TOP50 ticker: {ticker}"
            )

        full_features = build_ticker_features(
            ticker_history,
            calendar,
        )

        selected_dates = ticker_dates[ticker]

        selected = full_features[
            full_features["tradedate"].isin(selected_dates)
        ].copy()

        chunks.append(selected)

        if number % 50 == 0 or number == len(selected_tickers):
            log(
                f"Processed tickers: "
                f"{number:,}/{len(selected_tickers):,}"
            )

    if not chunks:
        raise RuntimeError(
            "No primitive feature rows were produced."
        )

    features = pd.concat(
        chunks,
        ignore_index=True,
    )

    features["tradedate"] = pd.to_datetime(
        features["tradedate"],
        errors="coerce",
    )

    frame = membership.merge(
        features,
        on=["tradedate", "secid"],
        how="left",
        validate="one_to_one",
    )

    # Cross-sectional relative-strength ranks are calculated only
    # within the PIT TOP50 cohort on each signal date.
    # Rank 1 means strongest.
    frame["rs_rank_20"] = (
        frame.groupby("tradedate")["return_20"]
        .rank(
            ascending=False,
            method="average",
        )
    )

    frame["rs_rank_60"] = (
        frame.groupby("tradedate")["return_60"]
        .rank(
            ascending=False,
            method="average",
        )
    )

    return frame


# ============================================================
# VALIDATION
# ============================================================

def validate_feature_frame(
    frame: pd.DataFrame,
    expected_rows: int,
) -> pd.DataFrame:
    log("Validating feature frame...")

    required_columns = {
        "tradedate",
        "secid",
        "rank",
        "universe_size",
        *CROSS_SECTIONAL_FEATURES,
    }

    missing = required_columns - set(frame.columns)

    if missing:
        raise RuntimeError(
            f"Feature frame is missing columns: {sorted(missing)}"
        )

    if len(frame) != expected_rows:
        raise RuntimeError(
            f"Row count mismatch: expected {expected_rows:,}, "
            f"got {len(frame):,}"
        )

    if frame.duplicated(
        ["tradedate", "secid"]
    ).any():
        raise RuntimeError(
            "Duplicate tradedate/SECID rows in feature frame."
        )

    if frame["tradedate"].isna().any():
        raise RuntimeError(
            "NULL tradedate values in feature frame."
        )

    if frame["secid"].isna().any():
        raise RuntimeError(
            "NULL SECID values in feature frame."
        )

    if frame["secid"].isin(EXCLUDED_TICKERS).any():
        raise RuntimeError(
            "Excluded tickers found in feature frame."
        )

    suspension_mask = (
        (frame["tradedate"] >= pd.Timestamp(SUSPENSION_START))
        & (frame["tradedate"] <= pd.Timestamp(SUSPENSION_END))
    )

    if suspension_mask.any():
        raise RuntimeError(
            "Suspension-period rows found in feature frame."
        )

    numeric_features = frame[
        CROSS_SECTIONAL_FEATURES
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    infinity_counts = np.isinf(
        numeric_features.to_numpy(dtype=float)
    ).sum(axis=0)

    if infinity_counts.sum() > 0:
        bad = {
            name: int(count)
            for name, count in zip(
                CROSS_SECTIONAL_FEATURES,
                infinity_counts,
            )
            if count > 0
        }

        raise RuntimeError(
            f"Infinite feature values found: {bad}"
        )

    quality_rows = []

    for feature in CROSS_SECTIONAL_FEATURES:
        values = numeric_features[feature]

        finite = values.notna()

        quality_rows.append({
            "feature": feature,
            "rows": int(len(values)),
            "valid_values": int(finite.sum()),
            "missing_values": int(values.isna().sum()),
            "missing_share": float(values.isna().mean()),
            "unique_values": int(values.nunique(dropna=True)),
            "minimum": (
                float(values.min())
                if finite.any() else np.nan
            ),
            "median": (
                float(values.median())
                if finite.any() else np.nan
            ),
            "maximum": (
                float(values.max())
                if finite.any() else np.nan
            ),
        })

    quality = pd.DataFrame(quality_rows)

    empty_features = quality.loc[
        quality["valid_values"].eq(0),
        "feature",
    ].tolist()

    if empty_features:
        raise RuntimeError(
            "Features contain no valid observations: "
            f"{empty_features}"
        )

    return quality


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    validate_inputs()
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    panel = load_panel()

    signal_panel = panel[
        panel["bar_available"].eq(1)
    ].copy()

    secids = sorted(
        panel["secid"].unique()
    )

    history, calendar = load_adjusted_history(
        secids
    )

    frame = build_feature_frame(
        panel,
        history,
        calendar,
    )

    quality = validate_feature_frame(
        frame,
        expected_rows=len(signal_panel),
    )

    # Stable column order.
    output_columns = [
        "tradedate",
        "secid",
        "rank",
        "universe_size",
        *CROSS_SECTIONAL_FEATURES,
    ]

    frame = frame[output_columns].copy()

    frame = frame.sort_values(
        ["tradedate", "rank", "secid"],
        kind="mergesort",
    ).reset_index(drop=True)

    log(f"Writing Parquet: {OUTPUT_PATH}")

    atomic_write_parquet(
        frame,
        OUTPUT_PATH,
    )

    quality.to_csv(
        QUALITY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    panel_stat = PANEL_PATH.stat()
    db_stat = ADJUSTED_DB_PATH.stat()

    metadata = {
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "script": (
            "scripts/experiments/primitives/"
            "05_build_primitive_features.py"
        ),

        "output_path": str(
            OUTPUT_PATH.relative_to(PROJECT_ROOT)
        ),

        "panel_path": str(
            PANEL_PATH.relative_to(PROJECT_ROOT)
        ),

        "adjusted_database_path": str(
            ADJUSTED_DB_PATH.relative_to(PROJECT_ROOT)
        ),

        "panel_file_size_bytes": int(
            panel_stat.st_size
        ),

        "panel_file_mtime_ns": int(
            panel_stat.st_mtime_ns
        ),

        "adjusted_database_size_bytes": int(
            db_stat.st_size
        ),

        "adjusted_database_mtime_ns": int(
            db_stat.st_mtime_ns
        ),

        "rows": int(len(frame)),
        "dates": int(frame["tradedate"].nunique()),
        "tickers": int(frame["secid"].nunique()),

        "date_from": str(
            frame["tradedate"].min().date()
        ),

        "date_till": str(
            frame["tradedate"].max().date()
        ),

        "feature_count": len(CROSS_SECTIONAL_FEATURES),
        "features": CROSS_SECTIONAL_FEATURES,

        "breadth_included": False,
        "forward_returns_included": False,
        "ic_calculated": False,
        "rank_ic_calculated": False,

        "signal_universe": (
            "Point-in-time TOP50 membership only; "
            "rows require bar_available == 1."
        ),

        "board_logic": {
            "activity": (
                "value and adjusted_volume summed across TQBR/EQBR"
            ),
            "ohlc": (
                "one board selected; complete OHLC first, "
                "then TQBR priority, EQBR fallback"
            ),
        },

        "excluded_tickers": sorted(
            EXCLUDED_TICKERS
        ),

        "excluded_suspension_interval": {
            "start": SUSPENSION_START,
            "end": SUSPENSION_END,
        },

        "missing_prices_forward_filled": False,
        "raw_database_modified": False,
        "adjusted_database_opened_read_only": True,

        "duplicate_tradedate_secid_rows": 0,
        "infinite_feature_values": 0,

        "missingness": {
            row["feature"]: {
                "missing_values": int(row["missing_values"]),
                "missing_share": float(row["missing_share"]),
            }
            for row in quality.to_dict("records")
        },
    }

    write_json(
        METADATA_PATH,
        metadata,
    )

    log("=" * 65)
    log("PRIMITIVE FEATURE FRAME COMPLETE")
    log(f"Rows: {len(frame):,}")
    log(f"Dates: {frame['tradedate'].nunique():,}")
    log(f"Tickers: {frame['secid'].nunique():,}")
    log(f"Features: {len(CROSS_SECTIONAL_FEATURES)}")
    log(f"Date range: {frame['tradedate'].min().date()} — "
        f"{frame['tradedate'].max().date()}")
    log(f"Parquet: {OUTPUT_PATH}")
    log(f"Metadata: {METADATA_PATH}")
    log(f"Quality report: {QUALITY_PATH}")
    log("=" * 65)


if __name__ == "__main__":
    main()
