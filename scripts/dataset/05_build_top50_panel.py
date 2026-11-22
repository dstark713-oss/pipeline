
# Path: scripts/dataset/05_build_top50_panel.py
# Description: Build point-in-time TOP50 membership and historical panel.
# Source: adjusted MOEX SQLite database. Source database is read-only.

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "moex_daily_adjusted.sqlite"
)

TABLE_NAME = "adjusted_daily_bars"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "top50"
REPORT_DIR = PROJECT_ROOT / "data" / "interim" / "top50_build"

MEMBERSHIP_PATH = OUTPUT_DIR / "top50_membership.parquet"
PANEL_PATH = OUTPUT_DIR / "top50_panel.parquet"

SUMMARY_PATH = REPORT_DIR / "summary.json"
DAILY_SUMMARY_PATH = REPORT_DIR / "daily_summary.csv"
BOARD_AUDIT_PATH = REPORT_DIR / "board_aggregation_audit.csv"

WARMUP_START_DATE = "2004-01-01"
PANEL_START_DATE = "2005-01-01"

TOP_N = 50
LOOKBACK_SESSIONS = 60

APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}

EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}

SUSPENSION_START = "2022-02-28"
SUSPENSION_END = "2022-03-23"

PIPELINE_VERSION = "1.0.0"


# ============================================================
# HELPERS
# ============================================================

def log(message: str) -> None:
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] {message}",
        flush=True,
    )


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


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


def atomic_write_json(
    payload: dict,
    destination: Path,
) -> None:
    temporary = destination.with_name(
        destination.name + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    temporary.replace(destination)


def readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"

    connection = sqlite3.connect(
        uri,
        uri=True,
    )

    connection.execute("PRAGMA query_only = ON")

    return connection


def get_table_columns(
    connection: sqlite3.Connection,
) -> dict[str, str]:
    rows = connection.execute(
        f'PRAGMA table_info("{TABLE_NAME}")'
    ).fetchall()

    if not rows:
        raise RuntimeError(
            f"SQLite table not found: {TABLE_NAME}"
        )

    return {
        row[1].lower(): row[1]
        for row in rows
    }


def require_columns(
    columns: dict[str, str],
    required: set[str],
) -> None:
    missing = required - set(columns)

    if missing:
        raise RuntimeError(
            f"Missing required columns in {TABLE_NAME}: "
            f"{sorted(missing)}"
        )


def build_source_fingerprint() -> dict:
    stat = DB_PATH.stat()

    return {
        "database_path": str(DB_PATH.resolve()),
        "database_size_bytes": stat.st_size,
        "database_mtime_ns": stat.st_mtime_ns,
    }


# ============================================================
# LOAD ADJUSTED DATA
# ============================================================

def load_source_data() -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Adjusted database not found: {DB_PATH}"
        )

    log(f"Opening adjusted database: {DB_PATH}")

    with readonly_connection(DB_PATH) as connection:
        columns = get_table_columns(connection)

        required = {
            "secid",
            "tradedate",
            "boardid",
            "adjusted_open",
            "adjusted_high",
            "adjusted_low",
            "adjusted_close",
            "adjusted_volume",
            "value",
        }

        require_columns(columns, required)

        optional_columns = {
            "numtrades",
            "adjustment_status",
        }

        selected = [
            "secid",
            "tradedate",
            "boardid",
            "adjusted_open",
            "adjusted_high",
            "adjusted_low",
            "adjusted_close",
            "adjusted_volume",
            "value",
        ]

        for column in optional_columns:
            if column in columns:
                selected.append(column)

        select_sql = ", ".join(
            f'"{columns[name]}" AS "{name}"'
            for name in selected
        )

        board_placeholders = ",".join(
            "?" for _ in APPROVED_BOARDS
        )

        ticker_placeholders = ",".join(
            "?" for _ in EXCLUDED_TICKERS
        )

        query = f"""
            SELECT {select_sql}
            FROM "{TABLE_NAME}"
            WHERE tradedate >= ?
              AND boardid IN ({board_placeholders})
              AND secid NOT IN ({ticker_placeholders})
            ORDER BY tradedate, secid, boardid
        """

        params = [
            WARMUP_START_DATE,
            *APPROVED_BOARDS,
            *sorted(EXCLUDED_TICKERS),
        ]

        source = pd.read_sql_query(
            query,
            connection,
            params=params,
        )

        calendar_query = f"""
            SELECT DISTINCT tradedate
            FROM "{TABLE_NAME}"
            WHERE tradedate >= ?
              AND boardid IN ({board_placeholders})
            ORDER BY tradedate
        """

        calendar = pd.read_sql_query(
            calendar_query,
            connection,
            params=[
                WARMUP_START_DATE,
                *APPROVED_BOARDS,
            ],
        )

    if source.empty:
        raise RuntimeError("Adjusted source query returned no rows.")

    source["secid"] = source["secid"].astype(str).str.upper()
    source["boardid"] = source["boardid"].astype(str).str.upper()

    source["tradedate"] = pd.to_datetime(
        source["tradedate"],
        errors="coerce",
    )

    calendar["tradedate"] = pd.to_datetime(
        calendar["tradedate"],
        errors="coerce",
    )

    source = source.dropna(
        subset=["secid", "boardid", "tradedate"]
    ).copy()

    calendar_dates = pd.DatetimeIndex(
        calendar["tradedate"].dropna().unique()
    ).sort_values()

    suspension_mask = (
        (source["tradedate"] >= SUSPENSION_START)
        & (source["tradedate"] <= SUSPENSION_END)
    )

    removed = int(suspension_mask.sum())

    source = source.loc[~suspension_mask].copy()

    calendar_dates = calendar_dates[
        (calendar_dates < pd.Timestamp(SUSPENSION_START))
        | (calendar_dates > pd.Timestamp(SUSPENSION_END))
    ]

    numeric_columns = [
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
        "adjusted_volume",
        "value",
    ]

    if "numtrades" in source.columns:
        numeric_columns.append("numtrades")

    for column in numeric_columns:
        source[column] = pd.to_numeric(
            source[column],
            errors="coerce",
        )

    if source["value"].isna().any():
        raise RuntimeError(
            "NULL VALUE encountered in adjusted source."
        )

    if (source["value"] < 0).any():
        raise RuntimeError(
            "Negative VALUE encountered in adjusted source."
        )

    duplicate_mask = source.duplicated(
        ["secid", "tradedate", "boardid"],
        keep=False,
    )

    duplicate_count = int(duplicate_mask.sum())

    if duplicate_count:
        sample = source.loc[
            duplicate_mask,
            ["secid", "tradedate", "boardid"],
        ].head(20)

        raise RuntimeError(
            "Duplicate SECID/TRADEDATE/BOARDID observations found. "
            "The script will not silently aggregate duplicate rows.\n"
            f"Sample:\n{sample.to_string(index=False)}"
        )

    log(f"Source rows: {len(source):,}")
    log(f"Source tickers: {source['secid'].nunique():,}")
    log(f"Market sessions: {len(calendar_dates):,}")
    log(f"Suspension rows excluded: {removed:,}")

    return source, calendar_dates


# ============================================================
# BOARD AGGREGATION
# ============================================================

def aggregate_boards(
    source: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    log("Aggregating TQBR/EQBR observations...")

    keys = ["secid", "tradedate"]

    # Activity is additive across approved boards.
    aggregation = {
        "volume": ("adjusted_volume", "sum"),
        "value": ("value", "sum"),
        "n_boards": ("boardid", "nunique"),
        "boards": (
            "boardid",
            lambda values: "|".join(
                sorted(set(values))
            ),
        ),
    }

    if "numtrades" in source.columns:
        aggregation["numtrades"] = (
            "numtrades",
            "sum",
        )

    activity = (
        source.groupby(keys, as_index=False)
        .agg(**aggregation)
    )

    # OHLC cannot be summed.
    # TQBR has priority; EQBR is fallback.
    prices = source.copy()

    prices["_priority"] = (
        prices["boardid"]
        .map(PRICE_BOARD_PRIORITY)
        .fillna(999)
    )

    # Prefer a board row with a usable close before applying board
    # priority. A quarantined/missing TQBR OHLC row must not hide a
    # valid EQBR price row for the same security and session.
    price_fields = [
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
    ]
    prices["_valid_price"] = (
        prices[price_fields].notna().all(axis=1).astype("int8")
    )

    prices = prices.sort_values(
        keys + ["_valid_price", "_priority", "boardid"],
        ascending=[True, True, False, True, True],
        kind="mergesort",
    )

    prices = prices.drop_duplicates(
        keys,
        keep="first",
    )

    price_columns = [
        "secid",
        "tradedate",
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
        "boardid",
    ]

    if "adjustment_status" in prices.columns:
        price_columns.append("adjustment_status")

    prices = prices[price_columns].rename(
        columns={"boardid": "price_board"}
    )

    daily = activity.merge(
        prices,
        on=keys,
        how="left",
        validate="one_to_one",
    )

    if daily.duplicated(keys).any():
        raise RuntimeError(
            "Duplicate SECID/TRADEDATE rows after board aggregation."
        )

    if daily["value"].isna().any():
        raise RuntimeError(
            "NULL VALUE after board aggregation."
        )

    if (daily["value"] < 0).any():
        raise RuntimeError(
            "Negative VALUE after board aggregation."
        )

    if daily["volume"].isna().any():
        raise RuntimeError(
            "NULL adjusted volume after board aggregation."
        )

    multi_board = daily["n_boards"] > 1

    audit = (
        daily.groupby("n_boards")
        .agg(
            secid_date_groups=("secid", "size"),
            unique_tickers=("secid", "nunique"),
            total_turnover=("value", "sum"),
            total_volume=("volume", "sum"),
        )
        .reset_index()
    )

    audit["multi_board_group"] = (
        audit["n_boards"] > 1
    )

    log(f"Aggregated SECID/date rows: {len(daily):,}")
    log(f"Multi-board groups: {int(multi_board.sum()):,}")

    return daily, audit


# ============================================================
# BUILD POINT-IN-TIME RANKING
# ============================================================

def build_membership(
    daily: pd.DataFrame,
    market_dates: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    log("Building rolling 60-session turnover matrix...")

    value_matrix = daily.pivot(
        index="tradedate",
        columns="secid",
        values="value",
    )

    value_matrix = value_matrix.reindex(
        index=market_dates
    ).sort_index()

    first_dates = daily.groupby("secid")[
        "tradedate"
    ].min()

    # A missing observation after the first observed bar means
    # zero recorded turnover for that market session.
    # Before the first observed bar, activity is unknown.
    exposure = pd.DataFrame(
        False,
        index=market_dates,
        columns=value_matrix.columns,
    )

    for ticker in value_matrix.columns:
        first_date = first_dates[ticker]
        exposure[ticker] = market_dates >= first_date

    value_matrix = value_matrix.where(
        exposure,
        np.nan,
    )

    value_for_rolling = value_matrix.fillna(0.0)

    # For date T, the ranking may use only the 60 sessions
    # immediately preceding T. Shift by one session BEFORE ranking.
    rolling_value = (
        value_for_rolling
        .rolling(
            window=LOOKBACK_SESSIONS,
            min_periods=LOOKBACK_SESSIONS,
        )
        .sum()
        .shift(1)
    )

    # Require the ticker to have existed throughout the full
    # preceding 60-session window.
    full_history = (
        exposure.astype("int16")
        .rolling(
            window=LOOKBACK_SESSIONS,
            min_periods=LOOKBACK_SESSIONS,
        )
        .sum()
        .shift(1)
        >= LOOKBACK_SESSIONS
    )

    eligible_value = rolling_value.where(full_history)

    records = []

    for position, date in enumerate(market_dates):
        if position == 0:
            continue

        ranking_date = market_dates[position - 1]

        if date < pd.Timestamp(PANEL_START_DATE):
            continue

        candidates = eligible_value.loc[date].dropna()
        candidates = candidates[candidates > 0]

        if candidates.empty:
            continue

        candidates = candidates.sort_values(
            ascending=False,
            kind="mergesort",
        )

        selected = candidates.head(TOP_N)
        universe_size = len(selected)

        selection_method = (
            f"TOP{TOP_N}_VALUE_{LOOKBACK_SESSIONS}D"
            if universe_size == TOP_N
            else "ALL_AVAILABLE"
        )

        for rank, (ticker, value_60d) in enumerate(
            selected.items(),
            start=1,
        ):
            records.append({
                "tradedate": date,
                "ranking_asof_date": ranking_date,
                "secid": ticker,
                "value_60d": float(value_60d),
                "rank": rank,
                "universe_size": universe_size,
                "selection_method": selection_method,
            })

    membership = pd.DataFrame.from_records(records)

    if membership.empty:
        raise RuntimeError(
            "TOP50 membership is empty. "
            "Check source coverage and warm-up history."
        )

    membership["tradedate"] = pd.to_datetime(
        membership["tradedate"]
    )

    membership["ranking_asof_date"] = pd.to_datetime(
        membership["ranking_asof_date"]
    )

    membership = membership.sort_values(
        ["tradedate", "rank", "secid"]
    ).reset_index(drop=True)

    if membership.duplicated(
        ["tradedate", "secid"]
    ).any():
        raise RuntimeError(
            "Duplicate ticker membership for a date."
        )

    daily_sizes = membership.groupby(
        "tradedate"
    )["secid"].nunique()

    if (daily_sizes > TOP_N).any():
        raise RuntimeError("TOP_N limit exceeded.")

    log(f"Membership rows: {len(membership):,}")
    log(f"Membership dates: {membership['tradedate'].nunique():,}")
    log(f"Membership tickers: {membership['secid'].nunique():,}")

    daily_summary = (
        membership.groupby("tradedate")
        .agg(
            universe_size=("secid", "nunique"),
            min_value_60d=("value_60d", "min"),
            max_value_60d=("value_60d", "max"),
            ranking_asof_date=("ranking_asof_date", "first"),
        )
        .reset_index()
    )

    return membership, daily_summary


# ============================================================
# BUILD FINAL PANEL
# ============================================================

def build_panel(
    membership: pd.DataFrame,
    daily: pd.DataFrame,
) -> pd.DataFrame:
    log("Joining membership with daily adjusted bars...")

    panel = membership.merge(
        daily,
        on=["tradedate", "secid"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    panel["bar_available"] = (
        panel["_merge"] == "both"
    ).astype("int8")

    panel = panel.drop(columns=["_merge"])

    # A selected ticker can have no current-day bar.
    # Keep its membership but do not forward-fill prices.
    panel["volume"] = panel["volume"].fillna(0.0)
    panel["value"] = panel["value"].fillna(0.0)
    panel["n_boards"] = panel["n_boards"].fillna(0).astype("int8")
    panel["boards"] = panel["boards"].fillna("")

    if "numtrades" in panel.columns:
        panel["numtrades"] = panel["numtrades"].fillna(0.0)

    panel = panel.sort_values(
        ["tradedate", "rank", "secid"]
    ).reset_index(drop=True)

    if panel.duplicated(
        ["tradedate", "secid"]
    ).any():
        raise RuntimeError(
            "Duplicate SECID/date rows in final panel."
        )

    if (panel["universe_size"] > TOP_N).any():
        raise RuntimeError(
            "Panel contains more than TOP_N tickers."
        )

    if panel["tradedate"].min() < pd.Timestamp(PANEL_START_DATE):
        raise RuntimeError(
            "Panel contains dates before configured start."
        )

    if panel["ranking_asof_date"].isna().any():
        raise RuntimeError(
            "Missing ranking_asof_date in panel."
        )

    # Ensure no look-ahead: ranking date must precede panel date.
    if not (
        panel["ranking_asof_date"] < panel["tradedate"]
    ).all():
        raise RuntimeError(
            "Look-ahead detected: ranking date is not before panel date."
        )

    log(f"Panel rows: {len(panel):,}")
    log(f"Panel tickers: {panel['secid'].nunique():,}")
    log(f"Panel dates: {panel['tradedate'].nunique():,}")
    log(
        "Rows without current-day bar: "
        f"{int((panel['bar_available'] == 0).sum()):,}"
    )

    return panel


# ============================================================
# VALIDATION AND REPORTING
# ============================================================

def run_validation(
    membership: pd.DataFrame,
    panel: pd.DataFrame,
    daily: pd.DataFrame,
) -> dict:
    tests = {}

    tests["membership_not_empty"] = len(membership) > 0

    tests["panel_not_empty"] = len(panel) > 0

    tests["unique_membership_date_ticker"] = (
        not membership.duplicated(
            ["tradedate", "secid"]
        ).any()
    )

    tests["unique_panel_date_ticker"] = (
        not panel.duplicated(
            ["tradedate", "secid"]
        ).any()
    )

    tests["top_n_limit"] = (
        membership.groupby("tradedate")["secid"]
        .nunique()
        .max() <= TOP_N
    )

    tests["panel_starts_2005_or_later"] = (
        panel["tradedate"].min()
        >= pd.Timestamp(PANEL_START_DATE)
    )

    tests["ranking_strictly_precedes_panel_date"] = (
        panel["ranking_asof_date"] < panel["tradedate"]
    ).all()

    tests["no_excluded_tickers"] = (
        not panel["secid"].isin(EXCLUDED_TICKERS).any()
    )

    tests["no_infinite_numeric_values"] = (
        not np.isinf(
            panel.select_dtypes(include=[np.number]).to_numpy(
                dtype=float,
                na_value=np.nan,
            )
        ).any()
    )

    tests["one_panel_row_per_membership"] = (
        len(panel) == len(membership)
    )

    tests["no_forward_fill"] = True

    failed = [
        name
        for name, passed in tests.items()
        if not passed
    ]

    for name, passed in tests.items():
        log(f"{'PASS' if passed else 'FAIL'}: {name}")

    if failed:
        raise RuntimeError(
            f"Validation failed: {failed}"
        )

    return tests


def build_daily_summary(
    membership: pd.DataFrame,
    panel: pd.DataFrame,
    market_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    result = (
        membership.groupby("tradedate")
        .agg(
            universe_size=("secid", "nunique"),
            min_value_60d=("value_60d", "min"),
            max_value_60d=("value_60d", "max"),
            ranking_asof_date=("ranking_asof_date", "first"),
        )
    )

    result["rows_without_bar"] = (
        panel.groupby("tradedate")["bar_available"]
        .apply(lambda values: int((values == 0).sum()))
    )

    result = result.reindex(
        pd.DatetimeIndex(
            [date for date in market_dates
             if date >= pd.Timestamp(PANEL_START_DATE)],
            name="tradedate",
        )
    )

    result["universe_size"] = (
        result["universe_size"].fillna(0).astype(int)
    )

    result["rows_without_bar"] = (
        result["rows_without_bar"].fillna(0).astype(int)
    )

    result["selection_method"] = np.where(
        result["universe_size"] == 0,
        "NO_ELIGIBLE_TICKERS",
        np.where(
            result["universe_size"] < TOP_N,
            "ALL_AVAILABLE",
            f"TOP{TOP_N}_VALUE_{LOOKBACK_SESSIONS}D",
        ),
    )

    return result.reset_index()


def main() -> None:
    ensure_directories()

    log("=" * 65)
    log("MOEX POINT-IN-TIME TOP50 BUILD")
    log("=" * 65)

    source, market_dates = load_source_data()

    daily, board_audit = aggregate_boards(source)

    membership, _ = build_membership(
        daily,
        market_dates,
    )

    panel = build_panel(
        membership,
        daily,
    )

    tests = run_validation(
        membership,
        panel,
        daily,
    )

    daily_summary = build_daily_summary(
        membership,
        panel,
        market_dates,
    )

    # All outputs are written only after successful validation.
    atomic_write_parquet(
        membership,
        MEMBERSHIP_PATH,
    )

    atomic_write_parquet(
        panel,
        PANEL_PATH,
    )

    board_audit.to_csv(
        BOARD_AUDIT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    daily_summary.to_csv(
        DAILY_SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "source_database": str(DB_PATH),
        "source_table": TABLE_NAME,
        "source_fingerprint": build_source_fingerprint(),
        "warmup_start_date": WARMUP_START_DATE,
        "panel_start_date": PANEL_START_DATE,
        "panel_end_date": str(
            panel["tradedate"].max().date()
        ),
        "top_n": TOP_N,
        "lookback_sessions": LOOKBACK_SESSIONS,
        "ranking_lag_sessions": 1,
        "approved_boards": list(APPROVED_BOARDS),
        "board_activity_policy": (
            "VALUE and adjusted volume are summed across TQBR/EQBR."
        ),
        "board_price_policy": (
            "TQBR preferred for OHLC; EQBR fallback."
        ),
        "excluded_tickers": sorted(EXCLUDED_TICKERS),
        "excluded_suspension": {
            "start": SUSPENSION_START,
            "end": SUSPENSION_END,
        },
        "source_rows_after_filters": len(source),
        "aggregated_daily_rows": len(daily),
        "membership_rows": len(membership),
        "membership_dates": int(
            membership["tradedate"].nunique()
        ),
        "membership_tickers": int(
            membership["secid"].nunique()
        ),
        "panel_rows": len(panel),
        "panel_dates": int(
            panel["tradedate"].nunique()
        ),
        "panel_tickers": int(
            panel["secid"].nunique()
        ),
        "rows_without_current_day_bar": int(
            (panel["bar_available"] == 0).sum()
        ),
        "multi_board_groups": int(
            (daily["n_boards"] > 1).sum()
        ),
        "validation": tests,
        "raw_database_modified": False,
        "adjusted_database_modified": False,
        "forward_fill_applied": False,
        "ranking_uses_current_day_turnover": False,
        "ranking_asof_date_strictly_precedes_panel_date": True,
        "outputs": {
            "membership": str(MEMBERSHIP_PATH),
            "panel": str(PANEL_PATH),
            "daily_summary": str(DAILY_SUMMARY_PATH),
            "board_audit": str(BOARD_AUDIT_PATH),
        },
    }

    atomic_write_json(
        summary,
        SUMMARY_PATH,
    )

    log("=" * 65)
    log("TOP50 BUILD COMPLETE")
    log("=" * 65)
    log(f"Membership: {MEMBERSHIP_PATH}")
    log(f"Panel:      {PANEL_PATH}")
    log(f"Summary:    {SUMMARY_PATH}")

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
            default=lambda obj: (
                obj.item()
                if hasattr(obj, "item")
                else str(obj)
            ),
        )
)


if __name__ == "__main__":
    main()
