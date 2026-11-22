
# Path: scripts/dataset/03_audit_raw_database.py
# Description: Read-only QA audit of raw MOEX daily bars.
# Outputs coverage, gaps, duplicate, cross-board and OHLCV reports.

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DB = ROOT / "data" / "raw" / "moex_daily_raw.sqlite"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "raw_database_audit"

TABLE = "daily_bars_raw"

COMPARE_FIELDS = [
    "numtrades",
    "value",
    "volume",
    "open",
    "high",
    "low",
    "legalcloseprice",
    "waprice",
    "close",
    "marketprice2",
    "marketprice3",
    "admittedquote",
    "admittedvalue",
]

PRICE_FIELDS = ["open", "high", "low", "close"]

CSV_SCHEMAS = {
    "ticker_coverage.csv": [
        "secid", "first_date", "last_date", "raw_rows",
        "unique_dates", "boards", "calendar_dates_in_span",
        "missing_calendar_dates", "missing_ratio",
        "history_incomplete",
    ],
    "ticker_year_coverage.csv": [
        "secid", "year", "raw_rows", "unique_dates",
        "first_date", "last_date", "boards",
    ],
    "board_year_coverage.csv": [
        "boardid", "year", "raw_rows", "unique_dates",
        "first_date", "last_date",
    ],
    "date_gaps.csv": [
        "secid", "gap_start", "gap_end", "missing_market_dates",
        "previous_observed_date", "next_observed_date",
    ],
    "duplicate_ticker_dates.csv": [
        "secid", "tradedate", "row_count", "board_count",
        "boards", "sessions",
    ],
    "overlapping_board_dates.csv": [
        "secid", "tradedate", "boards", "row_count",
        "differing_fields", "has_differences", "board_values",
    ],
    "data_quality_flags.csv": [
        "secid", "boardid", "tradedate", "flag_type",
        "severity", "reason", "numtrades", "volume",
        "open", "high", "low", "close",
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read-only MOEX raw database audit."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value):
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def valid_date(value):
    if value is None:
        return None
    value = str(value)[:10]
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


def values_equal(a, b):
    if a is None or b is None:
        return a is None and b is None

    fa = safe_float(a)
    fb = safe_float(b)

    if fa is not None and fb is not None:
        return math.isclose(fa, fb, rel_tol=1e-9, abs_tol=1e-9)

    return str(a) == str(b)


def compact_json(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), default=str
    )


def check_ohlcv(row):
    flags = []

    prices = {
        field: safe_float(row.get(field))
        for field in PRICE_FIELDS
    }

    for field, value in prices.items():
        if value is not None and value < 0:
            flags.append((
                "negative_price", "high", f"{field.upper()} is negative"
            ))
        elif value == 0:
            flags.append((
                "zero_price", "medium", f"{field.upper()} equals zero"
            ))

    high = prices["high"]
    low = prices["low"]
    open_price = prices["open"]
    close = prices["close"]

    if high is not None and low is not None:
        if high < low:
            flags.append((
                "high_below_low", "high", "HIGH is below LOW"
            ))

        if open_price is not None and not low <= open_price <= high:
            flags.append((
                "open_outside_range", "medium",
                "OPEN is outside LOW-HIGH range"
            ))

        if close is not None and not low <= close <= high:
            flags.append((
                "close_outside_range", "medium",
                "CLOSE is outside LOW-HIGH range"
            ))

    numtrades = safe_float(row.get("numtrades"))
    volume = safe_float(row.get("volume"))
    value = safe_float(row.get("value"))

    for field, number in [
        ("numtrades", numtrades),
        ("volume", volume),
        ("value", value),
    ]:
        if number is not None and number < 0:
            flags.append((
                f"negative_{field}", "high",
                f"{field.upper()} is negative"
            ))

    if numtrades == 0:
        flags.append(("zero_trades", "info", "NUMTRADES equals zero"))

    if volume == 0:
        flags.append(("zero_volume", "info", "VOLUME equals zero"))

    if numtrades is not None and numtrades > 0 and volume == 0:
        flags.append((
            "trades_without_volume", "medium",
            "NUMTRADES > 0 while VOLUME equals zero"
        ))

    if (
        numtrades is not None and numtrades == 0
        and volume is not None and volume > 0
    ):
        flags.append((
            "volume_without_trades", "medium",
            "VOLUME > 0 while NUMTRADES equals zero"
        ))

    return flags


def consecutive_groups(indices):
    if not indices:
        return []

    groups = [[indices[0]]]
    for index in indices[1:]:
        if index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def inspect_schema(conn):
    exists = conn.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (TABLE,),
    ).fetchone()

    if not exists:
        raise RuntimeError(f"Table {TABLE!r} not found.")

    schema = conn.execute(
        f'PRAGMA table_info("{TABLE}")'
    ).fetchall()

    columns = {row["name"].lower(): row["name"] for row in schema}

    required = {
        "secid", "boardid", "tradedate", "numtrades",
        "volume", "open", "high", "low", "close",
    }

    missing = required - set(columns)

    if missing:
        raise RuntimeError(f"Missing required columns: {sorted(missing)}")

    return columns


def run_audit(db_path, output_dir):
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    # URI read-only connection. No database writes are possible.
    conn = sqlite3.connect(
        f"file:{db_path.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    conn.row_factory = sqlite3.Row

    try:
        columns = inspect_schema(conn)

        selected = [
            "secid", "boardid", "tradedate",
            "tradingsession", "numtrades", "value",
            "volume", "open", "low", "high",
            "legalcloseprice", "waprice", "close",
            "marketprice2", "marketprice3",
            "admittedquote", "admittedvalue",
        ]

        available = [field for field in selected if field in columns]

        sql_columns = ", ".join(
            f'"{columns[field]}" AS "{field}"'
            for field in available
        )

        total_rows = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE}"
        ).fetchone()[0]

        ticker_dates = defaultdict(set)
        ticker_board_dates = defaultdict(set)
        ticker_year = defaultdict(
            lambda: {"rows": 0, "dates": set(), "boards": set()}
        )
        board_year = defaultdict(
            lambda: {"rows": 0, "dates": set()}
        )

        ticker_rows = Counter()
        board_rows = Counter()
        session_rows = Counter()
        ticker_date_rows = defaultdict(list)
        quality_flags = []

        invalid_date_rows = 0
        processed = 0

        query = (
            f"SELECT {sql_columns} FROM {TABLE} "
            "ORDER BY secid, tradedate, boardid"
        )

        for item in conn.execute(query):
            row = dict(item)
            processed += 1

            secid = str(row["secid"])
            board = str(row["boardid"])
            trade_date = valid_date(row["tradedate"])

            ticker_rows[secid] += 1
            board_rows[board] += 1
            session_rows[str(row.get("tradingsession"))] += 1

            if trade_date is None:
                invalid_date_rows += 1
                continue

            year = trade_date[:4]

            ticker_dates[secid].add(trade_date)
            ticker_board_dates[(secid, board)].add(trade_date)
            ticker_date_rows[(secid, trade_date)].append(row)

            ts = ticker_year[(secid, year)]
            ts["rows"] += 1
            ts["dates"].add(trade_date)
            ts["boards"].add(board)

            bs = board_year[(board, year)]
            bs["rows"] += 1
            bs["dates"].add(trade_date)

            for flag_type, severity, reason in check_ohlcv(row):
                quality_flags.append({
                    "secid": secid,
                    "boardid": board,
                    "tradedate": trade_date,
                    "flag_type": flag_type,
                    "severity": severity,
                    "reason": reason,
                    "numtrades": row.get("numtrades"),
                    "volume": row.get("volume"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                })

        # The calendar is observed in this dataset, not official MOEX calendar.
        calendar = sorted({
            d for dates in ticker_dates.values() for d in dates
        })
        calendar_index = {d: i for i, d in enumerate(calendar)}

        ticker_coverage = []
        date_gaps = []
        incomplete_count = 0

        for secid, dates in sorted(ticker_dates.items()):
            ordered = sorted(dates)
            first_date, last_date = ordered[0], ordered[-1]

            first_i = calendar_index[first_date]
            last_i = calendar_index[last_date]
            span = calendar[first_i:last_i + 1]

            missing = [d for d in span if d not in dates]
            ratio = len(missing) / len(span) if span else 0.0

            # Heuristic only. Illiquid securities may naturally have no row.
            incomplete = ratio > 0.05
            incomplete_count += int(incomplete)

            boards = sorted(
                b for s, b in ticker_board_dates if s == secid
            )

            ticker_coverage.append({
                "secid": secid,
                "first_date": first_date,
                "last_date": last_date,
                "raw_rows": ticker_rows[secid],
                "unique_dates": len(dates),
                "boards": "|".join(boards),
                "calendar_dates_in_span": len(span),
                "missing_calendar_dates": len(missing),
                "missing_ratio": round(ratio, 6),
                "history_incomplete": incomplete,
            })

            missing_indices = [calendar_index[d] for d in missing]

            for group in consecutive_groups(missing_indices):
                date_gaps.append({
                    "secid": secid,
                    "gap_start": calendar[group[0]],
                    "gap_end": calendar[group[-1]],
                    "missing_market_dates": len(group),
                    "previous_observed_date": (
                        calendar[group[0] - 1] if group[0] > 0 else None
                    ),
                    "next_observed_date": (
                        calendar[group[-1] + 1]
                        if group[-1] + 1 < len(calendar) else None
                    ),
                })

        ticker_year_coverage = []
        for (secid, year), stats in sorted(ticker_year.items()):
            dates = sorted(stats["dates"])
            ticker_year_coverage.append({
                "secid": secid,
                "year": year,
                "raw_rows": stats["rows"],
                "unique_dates": len(stats["dates"]),
                "first_date": dates[0],
                "last_date": dates[-1],
                "boards": "|".join(sorted(stats["boards"])),
            })

        board_year_coverage = []
        for (board, year), stats in sorted(board_year.items()):
            dates = sorted(stats["dates"])
            board_year_coverage.append({
                "boardid": board,
                "year": year,
                "raw_rows": stats["rows"],
                "unique_dates": len(stats["dates"]),
                "first_date": dates[0],
                "last_date": dates[-1],
            })

        duplicate_dates = []
        board_overlaps = []
        duplicate_groups = 0
        cross_board_groups = 0
        mismatch_groups = 0

        for (secid, trade_date), rows in sorted(ticker_date_rows.items()):
            if len(rows) <= 1:
                continue

            boards = sorted({str(r["boardid"]) for r in rows})
            duplicate_groups += 1

            duplicate_dates.append({
                "secid": secid,
                "tradedate": trade_date,
                "row_count": len(rows),
                "board_count": len(boards),
                "boards": "|".join(boards),
                "sessions": "|".join(sorted({
                    str(r.get("tradingsession")) for r in rows
                })),
            })

            if len(boards) <= 1:
                continue

            cross_board_groups += 1
            differing = []

            for field in COMPARE_FIELDS:
                if field not in columns:
                    continue

                values = [r.get(field) for r in rows]
                if any(
                    not values_equal(values[0], value)
                    for value in values[1:]
                ):
                    differing.append(field)

            if differing:
                mismatch_groups += 1

            board_overlaps.append({
                "secid": secid,
                "tradedate": trade_date,
                "boards": "|".join(boards),
                "row_count": len(rows),
                "differing_fields": "|".join(differing),
                "has_differences": bool(differing),
                "board_values": compact_json([
                    {
                        "boardid": r.get("boardid"),
                        **{f: r.get(f) for f in COMPARE_FIELDS
                           if f in columns},
                    }
                    for r in rows
                ]),
            })

        severity_counts = Counter(
            r["severity"] for r in quality_flags
        )
        type_counts = Counter(
            r["flag_type"] for r in quality_flags
        )

        summary = {
            "database": str(db_path),
            "table": TABLE,
            "audit_mode": "read_only",
            "raw_rows": total_rows,
            "rows_processed": processed,
            "invalid_date_rows": invalid_date_rows,
            "unique_secids": len(ticker_dates),
            "unique_boards": len(board_rows),
            "observed_market_dates": len(calendar),
            "first_date": calendar[0] if calendar else None,
            "last_date": calendar[-1] if calendar else None,
            "rows_by_board": dict(sorted(board_rows.items())),
            "rows_by_tradingsession": dict(sorted(session_rows.items())),
            "duplicate_ticker_date_groups": duplicate_groups,
            "cross_board_overlap_groups": cross_board_groups,
            "cross_board_mismatch_groups": mismatch_groups,
            "tickers_history_incomplete_heuristic": incomplete_count,
            "date_gap_intervals": len(date_gaps),
            "quality_flag_rows": len(quality_flags),
            "flags_by_severity": dict(severity_counts),
            "flags_by_type": dict(type_counts),
            "methodology": {
                "calendar": "Observed dates in downloaded database.",
                "gap_policy": (
                    "Missing observations are candidates for review, "
                    "not confirmed missing bars."
                ),
                "incomplete_threshold": (
                    "missing / observed calendar dates in ticker span > 5%"
                ),
                "cleaning_performed": False,
                "raw_database_modified": False,
            },
        }

        outputs = {
            "ticker_coverage.csv": ticker_coverage,
            "ticker_year_coverage.csv": ticker_year_coverage,
            "board_year_coverage.csv": board_year_coverage,
            "date_gaps.csv": date_gaps,
            "duplicate_ticker_dates.csv": duplicate_dates,
            "overlapping_board_dates.csv": board_overlaps,
            "data_quality_flags.csv": quality_flags,
        }

        for filename, rows in outputs.items():
            write_csv(
                output_dir / filename,
                rows,
                CSV_SCHEMAS[filename],
            )

        with (output_dir / "audit_summary.json").open(
            "w", encoding="utf-8"
        ) as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        return summary

    finally:
        conn.close()


def main():
    args = parse_args()

    summary = run_audit(args.db, args.output_dir)

    print("=" * 60)
    print("MOEX RAW DATABASE AUDIT")
    print("=" * 60)
    print(f"Raw rows:                 {summary['raw_rows']:,}")
    print(f"Rows processed:           {summary['rows_processed']:,}")
    print(f"Unique securities:        {summary['unique_secids']:,}")
    print(f"Unique boards:            {summary['unique_boards']}")
    print(f"Observed market dates:    {summary['observed_market_dates']:,}")
    print(f"Date range:               {summary['first_date']} -> {summary['last_date']}")
    print("-" * 60)
    print(f"Duplicate ticker/date:    {summary['duplicate_ticker_date_groups']:,}")
    print(f"Cross-board overlaps:     {summary['cross_board_overlap_groups']:,}")
    print(f"Cross-board mismatches:   {summary['cross_board_mismatch_groups']:,}")
    print(f"Incomplete history flags:{summary['tickers_history_incomplete_heuristic']:>7,}")
    print(f"Date gap intervals:       {summary['date_gap_intervals']:,}")
    print(f"Quality flag rows:        {summary['quality_flag_rows']:,}")
    print("-" * 60)

    print("Rows by board:")
    for board, count in summary["rows_by_board"].items():
        print(f"  {board}: {count:,}")

    print("Flags by type:")
    for flag, count in sorted(summary["flags_by_type"].items()):
        print(f"  {flag}: {count:,}")

    print("-" * 60)
    print("Raw database modified: NO")
    print(f"Reports: {args.output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
