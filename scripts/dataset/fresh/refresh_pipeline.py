# Path: pipeline/scripts/dataset/fresh/refresh_pipeline.py
# Description: Incrementally download new MOEX daily bars, rebuild adjusted
# data and the point-in-time TOP50 panel, then write a refresh report.
#
# Run from any working directory:
#   python scripts/dataset/fresh/refresh_pipeline.py
#
# The raw database is append-only. Existing observations are never updated
# or deleted. Failed board downloads stop publication of adjusted/panel data.

from __future__ import annotations

import csv
import importlib.util
import json
import logging
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

UNIVERSE_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "historical_universe"
    / "universe_common_shares.csv"
)
BOARD_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "historical_universe"
    / "universe_board_history.csv"
)

RAW_DB_PATH = PROJECT_ROOT / "data" / "raw" / "moex_daily_raw.sqlite"
ADJUSTED_BUILDER_PATH = (
    PROJECT_ROOT / "scripts" / "dataset" / "04_build_adjusted_dataset.py"
)
PANEL_BUILDER_PATH = (
    PROJECT_ROOT / "scripts" / "dataset" / "05_build_top50_panel.py"
)

REPORT_DIR = PROJECT_ROOT / "data" / "interim" / "fresh"
SUMMARY_PATH = REPORT_DIR / "refresh_summary.json"
ERRORS_PATH = REPORT_DIR / "refresh_errors.csv"

ALLOWED_BOARDS = {"TQBR", "EQBR"}
REQUEST_DELAY_SECONDS = 0.25
MAX_RETRIES = 5
PAGE_SIZE = 100

# Do not request the current calendar day. MOEX daily candles can still be
# incomplete while the session is in progress. Yesterday is a safe cutoff.
END_DATE = date.today() - timedelta(days=1)

LOG = logging.getLogger("pipeline.fresh_refresh")


# ============================================================
# IMPORT EXISTING PIPELINE IMPLEMENTATIONS
# ============================================================

def load_module(module_name: str, path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required pipeline script not found: {path}")

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Python module: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def write_json_atomic(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(destination)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        return list(reader)


# ============================================================
# RAW DATABASE REFRESH STATE
# ============================================================

def create_refresh_state(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS fresh_board_state (
            secid TEXT NOT NULL,
            boardid TEXT NOT NULL,
            last_checked_through TEXT NOT NULL,
            last_status TEXT NOT NULL,
            last_rows_received INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (secid, boardid)
        )
        """
    )
    connection.commit()


def load_board_pairs(
    universe_rows: list[dict[str, str]],
    board_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    universe = {
        (row.get("SECID") or "").strip().upper()
        for row in universe_rows
    }
    universe.discard("")

    ranges: dict[tuple[str, str], str] = {}

    for row in board_rows:
        secid = (row.get("SECID") or "").strip().upper()
        board = (row.get("BOARDID") or "").strip().upper()
        history_from = (row.get("history_from") or "").strip()

        if secid not in universe or board not in ALLOWED_BOARDS:
            continue
        if not history_from:
            continue

        try:
            date.fromisoformat(history_from)
        except ValueError:
            LOG.warning("Skipping invalid history_from: %s/%s %s", secid, board, history_from)
            continue

        key = (secid, board)
        ranges[key] = min(ranges.get(key, history_from), history_from)

    return [
        {"secid": secid, "boardid": board, "history_from": start}
        for (secid, board), start in sorted(ranges.items())
    ]


def get_last_observation(
    connection: sqlite3.Connection,
    secid: str,
    board: str,
) -> str | None:
    row = connection.execute(
        """
        SELECT MAX(tradedate)
        FROM daily_bars_raw
        WHERE secid = ? AND boardid = ?
        """,
        (secid, board),
    ).fetchone()
    return row[0] if row and row[0] else None


def get_checked_through(
    connection: sqlite3.Connection,
    secid: str,
    board: str,
) -> str | None:
    row = connection.execute(
        """
        SELECT last_checked_through
        FROM fresh_board_state
        WHERE secid = ? AND boardid = ?
        """,
        (secid, board),
    ).fetchone()
    return row[0] if row else None


def save_board_state(
    connection: sqlite3.Connection,
    secid: str,
    board: str,
    checked_through: str,
    status: str,
    rows_received: int,
) -> None:
    connection.execute(
        """
        INSERT INTO fresh_board_state (
            secid, boardid, last_checked_through,
            last_status, last_rows_received, updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(secid, boardid) DO UPDATE SET
            last_checked_through = excluded.last_checked_through,
            last_status = excluded.last_status,
            last_rows_received = excluded.last_rows_received,
            updated_at = CURRENT_TIMESTAMP
        """,
        (secid, board, checked_through, status, rows_received),
    )
    connection.commit()


# ============================================================
# INCREMENTAL MOEX DOWNLOAD
# ============================================================

def fetch_board_range(
    downloader,
    connection: sqlite3.Connection,
    secid: str,
    board: str,
    start_date: str,
    end_date: str,
) -> tuple[int, int]:
    offset = 0
    received_total = 0
    inserted_total = 0

    while True:
        url = downloader.build_history_url(
            secid=secid,
            board=board,
            from_date=start_date,
            till_date=end_date,
            start=offset,
        )
        payload = downloader.request_json(
            url=url,
            max_retries=MAX_RETRIES,
            delay=REQUEST_DELAY_SECONDS,
        )
        _, rows = downloader.parse_history(payload)

        if not rows:
            break

        inserted = downloader.insert_history_rows(
            connection=connection,
            secid=secid,
            board=board,
            rows=rows,
        )
        connection.commit()

        received_total += len(rows)
        inserted_total += inserted
        offset += len(rows)

        LOG.info(
            "%s/%s %s..%s | received=%d inserted=%d",
            secid, board, start_date, end_date, len(rows), inserted,
        )

        if len(rows) < PAGE_SIZE:
            break

    return received_total, inserted_total


def update_raw_database() -> dict[str, Any]:
    if not RAW_DB_PATH.is_file():
        raise FileNotFoundError(f"Raw SQLite database not found: {RAW_DB_PATH}")

    universe_rows = read_csv(UNIVERSE_PATH)
    board_rows = read_csv(BOARD_HISTORY_PATH)
    pairs = load_board_pairs(universe_rows, board_rows)

    if not pairs:
        raise RuntimeError("No SECID/board pairs found in historical universe files.")

    downloader = load_module(
        "pipeline_raw_downloader",
        PROJECT_ROOT / "scripts" / "dataset" / "02_download_daily_bars_sqlite.py",
    )

    connection = sqlite3.connect(RAW_DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row

    attempted = 0
    successful = 0
    skipped = 0
    empty = 0
    received_total = 0
    inserted_total = 0
    errors: list[dict[str, str]] = []

    try:
        create_refresh_state(connection)

        required = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_bars_raw'"
        ).fetchone()
        if required is None:
            raise RuntimeError("daily_bars_raw table is missing from raw database.")

        for index, pair in enumerate(pairs, start=1):
            secid = pair["secid"]
            board = pair["boardid"]

            checked_through = get_checked_through(connection, secid, board)
            if checked_through is None:
                checked_through = get_last_observation(connection, secid, board)

            if checked_through is None:
                # Initial historical load is a separate, explicit stage.
                # Do not unexpectedly download decades of history here.
                skipped += 1
                errors.append({
                    "secid": secid,
                    "boardid": board,
                    "error": "No existing raw observations; run the historical downloader first.",
                })
                continue

            start_date = (
                date.fromisoformat(checked_through) + timedelta(days=1)
            ).isoformat()

            if start_date > END_DATE.isoformat():
                skipped += 1
                continue

            attempted += 1
            try:
                received, inserted = fetch_board_range(
                    downloader=downloader,
                    connection=connection,
                    secid=secid,
                    board=board,
                    start_date=start_date,
                    end_date=END_DATE.isoformat(),
                )

                received_total += received
                inserted_total += inserted
                successful += 1
                if received == 0:
                    empty += 1

                # Advance the checkpoint even when there were no trades:
                # this avoids repeatedly querying inactive securities.
                save_board_state(
                    connection,
                    secid,
                    board,
                    END_DATE.isoformat(),
                    "complete",
                    received,
                )

            except Exception as exc:
                connection.rollback()
                error_text = f"{type(exc).__name__}: {exc}"
                errors.append({
                    "secid": secid,
                    "boardid": board,
                    "error": error_text,
                })
                save_board_state(
                    connection,
                    secid,
                    board,
                    checked_through,
                    "error",
                    0,
                )
                LOG.exception("Refresh failed for %s/%s", secid, board)

            if index % 50 == 0 or index == len(pairs):
                LOG.info(
                    "Download progress %d/%d | attempted=%d successful=%d "
                    "empty=%d skipped=%d errors=%d inserted=%d",
                    index, len(pairs), attempted, successful,
                    empty, skipped, len(errors), inserted_total,
                )

            time.sleep(REQUEST_DELAY_SECONDS)

    finally:
        connection.close()

    result = {
        "end_date_checked": END_DATE.isoformat(),
        "board_pairs_total": len(pairs),
        "attempted": attempted,
        "successful": successful,
        "empty": empty,
        "skipped": skipped,
        "errors": len(errors),
        "rows_received": received_total,
        "rows_inserted": inserted_total,
        "raw_database": str(RAW_DB_PATH),
    }

    return {"summary": result, "errors": errors}


def write_errors(errors: list[dict[str, str]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = ERRORS_PATH.with_name(ERRORS_PATH.name + ".tmp")
    fields = ["secid", "boardid", "error"]

    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(errors)

    temporary.replace(ERRORS_PATH)


# ============================================================
# REBUILD DERIVED DATASETS
# ============================================================

def rebuild_adjusted_and_panel() -> dict[str, Any]:
    adjusted = load_module(
        "pipeline_adjusted_builder",
        ADJUSTED_BUILDER_PATH,
    )
    panel = load_module(
        "pipeline_top50_builder",
        PANEL_BUILDER_PATH,
    )

    LOG.info("Rebuilding adjusted SQLite database...")
    adjusted.build_adjusted_database()

    LOG.info("Rebuilding PIT TOP50 panel...")
    panel.main()

    summary_path = panel.SUMMARY_PATH
    if not summary_path.is_file():
        raise RuntimeError("TOP50 builder completed without producing summary.json.")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("validation") or not all(summary["validation"].values()):
        raise RuntimeError("TOP50 summary is missing successful validation results.")

    return {
        "adjusted_database": str(adjusted.OUTPUT_DB),
        "top50_panel": str(panel.PANEL_PATH),
        "top50_membership": str(panel.MEMBERSHIP_PATH),
        "top50_summary": str(summary_path),
        "panel_end_date": summary.get("panel_end_date"),
        "panel_rows": summary.get("panel_rows"),
        "validation": summary.get("validation"),
    }


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    LOG.info("=" * 72)
    LOG.info("MOEX DAILY REFRESH")
    LOG.info("Project root: %s", PROJECT_ROOT)
    LOG.info("Download cutoff: %s", END_DATE.isoformat())
    LOG.info("=" * 72)

    started_at = datetime.now(timezone.utc).isoformat()

    download_result = update_raw_database()
    write_errors(download_result["errors"])

    download_summary = download_result["summary"]
    if download_summary["errors"] > 0:
        report = {
            "status": "FAILED_DOWNLOAD",
            "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "download": download_summary,
            "errors_file": str(ERRORS_PATH),
            "derived_datasets_rebuilt": False,
            "reason": "At least one board download failed or has no existing raw history.",
        }
        write_json_atomic(report, SUMMARY_PATH)
        LOG.error(
            "Refresh stopped before rebuilding derived data. "
            "Resolve download errors and rerun."
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    rebuild_summary = rebuild_adjusted_and_panel()

    report = {
        "status": "SUCCESS",
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "download": download_summary,
        "rebuild": rebuild_summary,
        "raw_database_modified_only_by_appending_new_rows": True,
        "raw_observations_deleted_or_updated": False,
        "current_calendar_day_requested": False,
        "forward_fill_applied": False,
    }

    write_json_atomic(report, SUMMARY_PATH)

    LOG.info("=" * 72)
    LOG.info("DAILY REFRESH COMPLETE")
    LOG.info("New raw rows: %s", download_summary["rows_inserted"])
    LOG.info("Panel end date: %s", rebuild_summary["panel_end_date"])
    LOG.info("Summary: %s", SUMMARY_PATH)
    LOG.info("=" * 72)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        LOG.warning("Interrupted. Committed raw pages and refresh checkpoints are preserved.")
        raise SystemExit(130)
    except Exception:
        LOG.exception("Daily refresh failed.")
        raise SystemExit(1)
