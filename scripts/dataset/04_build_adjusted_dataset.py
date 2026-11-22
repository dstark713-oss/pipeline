
# Path: scripts/dataset/04_build_adjusted_dataset.py
# Description: Builds a separate corporate-action-adjusted SQLite dataset.
# Raw MOEX database is read-only and is never modified.

import csv
import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DB = PROJECT_ROOT / "data" / "raw" / "moex_daily_raw.sqlite"
OUTPUT_DB = PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"

REPORT_DIR = PROJECT_ROOT / "data" / "interim" / "corporate_actions"
REGISTER_CSV = REPORT_DIR / "corporate_actions_register.csv"
AUDIT_CSV = REPORT_DIR / "adjustment_audit.csv"
SUMMARY_JSON = REPORT_DIR / "adjustment_summary.json"

SOURCE_TABLE = "daily_bars_raw"
TARGET_TABLE = "adjusted_daily_bars"
BATCH_SIZE = 5000


# Historical prices are divided by new_shares_per_old_share.
# Historical share volume is multiplied by new_shares_per_old_share.
# effective_date is the first trading date in the new price/share scale.

CORPORATE_ACTIONS = [
    {
        "action_id": "VTBR_2024_5000_TO_1",
        "secid": "VTBR",
        "action_type": "CONSOLIDATION",
        "ratio": "5000:1",
        "new_shares_per_old_share": 1 / 5000,
        "effective_date": "2024-07-15",
        "status": "APPLY",
        "source_url": "",
        "notes": "Confirmed in previous forensic review. Historical prices multiplied by 5000.",
    },
    {
        "action_id": "IRAO_2015_100_TO_1",
        "secid": "IRAO",
        "action_type": "CONSOLIDATION",
        "ratio": "100:1",
        "new_shares_per_old_share": 1 / 100,
        "effective_date": "2015-01-20",
        "status": "APPLY",
        "source_url": "",
        "notes": "Confirmed in previous forensic review. Historical prices multiplied by 100.",
    },
    {
        "action_id": "GMKN_2024_1_TO_100",
        "secid": "GMKN",
        "action_type": "SPLIT",
        "ratio": "1:100",
        "new_shares_per_old_share": 100,
        "effective_date": "2024-04-08",
        "status": "APPLY",
        "source_url": "",
        "notes": (
            "Confirmed 100-for-1 split. 2024-04-08 is the first post-action "
            "trading bar in the audited daily series."
        ),
    },
    {
        "action_id": "ROLO_2023_1_TO_10",
        "secid": "ROLO",
        "action_type": "SPLIT",
        "ratio": "1:10",
        "new_shares_per_old_share": 10,
        "effective_date": "2023-01-19",
        "status": "APPLY",
        "source_url": "",
        "notes": (
            "Confirmed 1:10 split. 2023-01-19 is the effective trading "
            "boundary used in the daily series."
        ),
    },
    {
        "action_id": "GEMA_2024_1_TO_10",
        "secid": "GEMA",
        "action_type": "SPLIT",
        "ratio": "1:10",
        "new_shares_per_old_share": 10,
        "effective_date": "2024-02-08",
        "status": "APPLY",
        "source_url": "",
        "notes": "Confirmed 1:10 split. Historical prices divided by 10.",
    },
    {
        "action_id": "PLZL_2025_1_TO_10",
        "secid": "PLZL",
        "action_type": "SPLIT",
        "ratio": "1:10",
        "new_shares_per_old_share": 10,
        "effective_date": "2025-03-27",
        "status": "APPLY",
        "source_url": "https://www.moex.com/n88888",
        "notes": (
            "Official MOEX notice: trading in the new scale resumed "
            "2025-03-27. Issuer confirmed the split and conversion "
            "on 2025-03-25."
        ),
    },
    {
        "action_id": "BELU_2024_1_TO_8",
        "secid": "BELU",
        "action_type": "ADDITIONAL_SHARE_DISTRIBUTION",
        "ratio": "1:8",
        "new_shares_per_old_share": 8,
        "effective_date": "2024-08-22",
        "status": "SPECIAL_HANDLING",
        "source_url": "",
        "notes": (
            "Seven additional shares per existing share. Historical bars "
            "before the effective date are adjusted 1:8. The 2024-08-22 "
            "OHLC bar is quarantined because its fields appear to contain "
            "mixed price scales."
        ),
    },
]


PRICE_FIELDS = [
    "open",
    "high",
    "low",
    "close",
    "legalcloseprice",
    "waprice",
    "marketprice2",
    "marketprice3",
    "admittedquote",
]

VOLUME_FIELDS = ["volume"]


def quote_identifier(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def sqlite_readonly_uri(path):
    absolute = path.resolve().as_posix()
    return f"file:{quote(absolute, safe='/:')}?mode=ro"


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def safe_multiply(value, factor):
    if value is None:
        return None

    try:
        return float(value) * factor
    except (TypeError, ValueError, OverflowError):
        return None


def get_actions_by_ticker():
    result = {}

    for action in CORPORATE_ACTIONS:
        secid = action["secid"]

        if secid in result:
            raise ValueError(
                f"Multiple corporate actions for {secid}. "
                "Chained-action logic must be implemented explicitly."
            )

        if float(action["new_shares_per_old_share"]) <= 0:
            raise ValueError(
                f"Invalid share factor for {action['action_id']}"
            )

        datetime.strptime(action["effective_date"], "%Y-%m-%d")
        result[secid] = action

    return result


def get_source_schema(source_conn):
    info = source_conn.execute(
        f"PRAGMA table_info({quote_identifier(SOURCE_TABLE)})"
    ).fetchall()

    if not info:
        raise ValueError(
            f"Source table '{SOURCE_TABLE}' does not exist."
        )

    # Normalized lookup makes the script insensitive to column casing.
    by_lower = {row[1].lower(): row[1] for row in info}

    required = {"secid", "tradedate", "volume"}
    missing = sorted(required - set(by_lower))

    if missing:
        raise ValueError(
            f"Missing required source columns: {missing}"
        )

    return info, by_lower


def create_target_table(target_conn, source_info, source_by_lower):
    definitions = []

    primary_key_columns = [
        row[1] for row in source_info if row[5] > 0
    ]

    for row in source_info:
        name = row[1]
        declared_type = row[2] or ""

        definition = quote_identifier(name)

        if declared_type:
            definition += f" {declared_type}"

        # Preserve a single-column primary key, if present.
        if len(primary_key_columns) == 1 and row[5] > 0:
            definition += " PRIMARY KEY"

        definitions.append(definition)

    for field in PRICE_FIELDS:
        if field in source_by_lower:
            definitions.append(
                f'{quote_identifier("adjusted_" + field)} REAL'
            )

    for field in VOLUME_FIELDS:
        if field in source_by_lower:
            definitions.append(
                f'{quote_identifier("adjusted_" + field)} REAL'
            )

    definitions.extend([
        '"price_adjustment_factor" REAL',
        '"volume_adjustment_factor" REAL',
        '"corporate_action_id" TEXT',
        '"adjustment_status" TEXT',
    ])

    target_conn.execute(
        f'CREATE TABLE {quote_identifier(TARGET_TABLE)} '
        f'({", ".join(definitions)})'
    )


def build_adjusted_database():
    if not RAW_DB.is_file():
        raise FileNotFoundError(
            f"Raw database not found: {RAW_DB}\n"
            "Expected path: data/raw/moex_daily_raw.sqlite"
        )

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    temp_db = OUTPUT_DB.with_name(
        OUTPUT_DB.stem + ".building.sqlite"
    )

    if temp_db.exists():
        temp_db.unlink()

    source_conn = None
    target_conn = None

    try:
        source_conn = sqlite3.connect(
            sqlite_readonly_uri(RAW_DB),
            uri=True,
        )
        source_conn.execute("PRAGMA query_only = ON")

        source_info, source_by_lower = get_source_schema(
            source_conn
        )

        source_columns = [row[1] for row in source_info]

        source_index = {
            name.lower(): position
            for position, name in enumerate(source_columns)
        }

        target_conn = sqlite3.connect(temp_db)
        target_conn.execute("PRAGMA journal_mode = DELETE")
        target_conn.execute("PRAGMA synchronous = FULL")

        create_target_table(
            target_conn,
            source_info,
            source_by_lower,
        )

        output_columns = list(source_columns)

        for field in PRICE_FIELDS:
            if field in source_by_lower:
                output_columns.append("adjusted_" + field)

        for field in VOLUME_FIELDS:
            if field in source_by_lower:
                output_columns.append("adjusted_" + field)

        output_columns.extend([
            "price_adjustment_factor",
            "volume_adjustment_factor",
            "corporate_action_id",
            "adjustment_status",
        ])

        insert_columns = ", ".join(
            quote_identifier(column)
            for column in output_columns
        )

        placeholders = ", ".join(
            "?" for _ in output_columns
        )

        insert_sql = (
            f'INSERT INTO {quote_identifier(TARGET_TABLE)} '
            f'({insert_columns}) VALUES ({placeholders})'
        )

        # Stable ordering makes repeatable builds easier to compare.
        id_column = source_by_lower.get("id")

        if id_column:
            select_sql = (
                f'SELECT * FROM {quote_identifier(SOURCE_TABLE)} '
                f'ORDER BY {quote_identifier(id_column)}'
            )
        else:
            select_sql = (
                f'SELECT * FROM {quote_identifier(SOURCE_TABLE)}'
            )

        source_cursor = source_conn.execute(select_sql)
        actions_by_ticker = get_actions_by_ticker()

        row_count = 0
        status_counts = Counter()
        action_counts = Counter()

        action_row_counts = {
            action["action_id"]: {
                "historical_rows_adjusted": 0,
                "effective_date_rows_quarantined": 0,
                "post_action_rows_unadjusted": 0,
            }
            for action in CORPORATE_ACTIONS
        }

        while True:
            batch = source_cursor.fetchmany(BATCH_SIZE)

            if not batch:
                break

            output_batch = []

            for raw_row in batch:
                row = list(raw_row)

                secid = row[source_index["secid"]]
                tradedate = row[source_index["tradedate"]]

                action = actions_by_ticker.get(secid)

                price_factor = 1.0
                volume_factor = 1.0
                action_id = None
                status = "UNADJUSTED_NO_ACTION"

                if action:
                    action_id = action["action_id"]
                    effective_date = action["effective_date"]

                    share_factor = float(
                        action["new_shares_per_old_share"]
                    )

                    if tradedate is None:
                        status = "UNADJUSTED_DATE_MISSING"

                    elif str(tradedate) < effective_date:
                        price_factor = 1.0 / share_factor
                        volume_factor = share_factor
                        status = "ADJUSTED"

                        action_row_counts[action_id][
                            "historical_rows_adjusted"
                        ] += 1

                    elif (
                        action["status"] == "SPECIAL_HANDLING"
                        and str(tradedate) == effective_date
                    ):
                        status = "QUARANTINED_MIXED_SCALE"

                        action_row_counts[action_id][
                            "effective_date_rows_quarantined"
                        ] += 1

                    else:
                        status = "POST_ACTION_NATIVE_SCALE"

                        action_row_counts[action_id][
                            "post_action_rows_unadjusted"
                        ] += 1

                adjusted_values = []

                for field in PRICE_FIELDS:
                    if field not in source_by_lower:
                        continue

                    raw_value = row[source_index[field]]

                    if status == "QUARANTINED_MIXED_SCALE":
                        adjusted_values.append(None)
                    else:
                        adjusted_values.append(
                            safe_multiply(
                                raw_value,
                                price_factor,
                            )
                        )

                for field in VOLUME_FIELDS:
                    if field not in source_by_lower:
                        continue

                    raw_value = row[source_index[field]]

                    adjusted_values.append(
                        safe_multiply(
                            raw_value,
                            volume_factor,
                        )
                    )

                stored_price_factor = (
                    None
                    if status == "QUARANTINED_MIXED_SCALE"
                    else price_factor
                )

                output_batch.append(
                    row
                    + adjusted_values
                    + [
                        stored_price_factor,
                        volume_factor,
                        action_id,
                        status,
                    ]
                )

                row_count += 1
                status_counts[status] += 1

                if action_id:
                    action_counts[action_id] += 1

            target_conn.executemany(
                insert_sql,
                output_batch,
            )
            target_conn.commit()

        secid_col = quote_identifier(
            source_by_lower["secid"]
        )
        date_col = quote_identifier(
            source_by_lower["tradedate"]
        )

        target_conn.execute(
            f'CREATE INDEX "idx_adjusted_secid_date" '
            f'ON {quote_identifier(TARGET_TABLE)} '
            f'({secid_col}, {date_col})'
        )

        board_column = source_by_lower.get("boardid")

        if board_column:
            target_conn.execute(
                f'CREATE INDEX "idx_adjusted_secid_board_date" '
                f'ON {quote_identifier(TARGET_TABLE)} '
                f'({secid_col}, {quote_identifier(board_column)}, '
                f'{date_col})'
            )

        target_conn.commit()

        source_count = source_conn.execute(
            f'SELECT COUNT(*) FROM {quote_identifier(SOURCE_TABLE)}'
        ).fetchone()[0]

        target_count = target_conn.execute(
            f'SELECT COUNT(*) FROM {quote_identifier(TARGET_TABLE)}'
        ).fetchone()[0]

        if (
            source_count != target_count
            or row_count != source_count
        ):
            raise RuntimeError(
                f"Row count mismatch: source={source_count}, "
                f"target={target_count}, processed={row_count}"
            )

        integrity = target_conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"SQLite integrity check failed: {integrity}"
            )

        # Close handles before replacing the final database.
        # This is important on Windows.
        target_conn.close()
        target_conn = None

        source_conn.close()
        source_conn = None

        os.replace(temp_db, OUTPUT_DB)

        audit_rows = []
        register_rows = []

        for action in CORPORATE_ACTIONS:
            counts = action_row_counts[action["action_id"]]

            audit_rows.append({
                "action_id": action["action_id"],
                "secid": action["secid"],
                "ratio": action["ratio"],
                "effective_date": action["effective_date"],
                "status": action["status"],
                **counts,
            })

            register_rows.append({
                "action_id": action["action_id"],
                "secid": action["secid"],
                "action_type": action["action_type"],
                "ratio": action["ratio"],
                "new_shares_per_old_share": (
                    action["new_shares_per_old_share"]
                ),
                "effective_date": action["effective_date"],
                "status": action["status"],
                "source_url": action["source_url"],
                "notes": action["notes"],
            })

        write_csv(
            REGISTER_CSV,
            register_rows,
            [
                "action_id",
                "secid",
                "action_type",
                "ratio",
                "new_shares_per_old_share",
                "effective_date",
                "status",
                "source_url",
                "notes",
            ],
        )

        write_csv(
            AUDIT_CSV,
            audit_rows,
            [
                "action_id",
                "secid",
                "ratio",
                "effective_date",
                "status",
                "historical_rows_adjusted",
                "effective_date_rows_quarantined",
                "post_action_rows_unadjusted",
            ],
        )

        summary = {
            "run_timestamp_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "source_database": str(RAW_DB),
            "output_database": str(OUTPUT_DB),
            "source_table": SOURCE_TABLE,
            "output_table": TARGET_TABLE,
            "source_rows": source_count,
            "output_rows": target_count,
            "rows_processed": row_count,
            "row_counts_match": source_count == target_count,
            "sqlite_integrity_check": integrity,
            "adjustment_status_counts": dict(status_counts),
            "corporate_action_row_counts": dict(action_counts),
            "corporate_actions": audit_rows,
            "raw_database_modified": False,
            "raw_database_opened_read_only": True,
            "price_adjustments_applied_only_to_confirmed_actions": True,
            "unconfirmed_actions_adjusted": [],
            "belu_effective_date_bar_quarantined": True,
            "automatic_outlier_removal": False,
            "forward_fill_applied": False,
            "source_rows_preserved_one_to_one": True,
            "board_rows_preserved_without_deduplication": True,
        }

        write_json(SUMMARY_JSON, summary)

        print(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            )
        )

        print("\nAdjusted dataset created successfully.")

    except Exception:
        if target_conn is not None:
            target_conn.close()

        if source_conn is not None:
            source_conn.close()

        if temp_db.exists():
            temp_db.unlink()

        raise


def main():
    build_adjusted_database()


if __name__ == "__main__":
    main()
