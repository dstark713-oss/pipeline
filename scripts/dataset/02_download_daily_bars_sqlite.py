
# Path: pipeline/scripts/dataset/02_download_daily_bars_sqlite.py
# Description: Downloads raw historical MOEX daily bars for the
# historical common-share universe into a resumable SQLite database.

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import random
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request

from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://iss.moex.com/iss"

ALLOWED_BOARDS = {"TQBR", "EQBR"}

PAGE_SIZE = 100
DEFAULT_DELAY = 0.25
MAX_RETRIES = 5
REQUEST_TIMEOUT = 60

LOG = logging.getLogger("pipeline.moex_raw_downloader")


# ============================================================
# ARGUMENTS
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download raw MOEX historical daily bars "
            "for the common-share universe into SQLite."
        )
    )

    parser.add_argument(
        "--universe-file",
        default=(
            "data/interim/historical_universe/"
            "universe_common_shares.csv"
        ),
    )

    parser.add_argument(
        "--board-history-file",
        default=(
            "data/interim/historical_universe/"
            "universe_board_history.csv"
        ),
    )

    parser.add_argument(
        "--db-path",
        default="data/raw/moex_daily_raw.sqlite",
    )

    # One year of warm-up before the panel period.
    parser.add_argument(
        "--from-date",
        default="2004-01-01",
    )

    parser.add_argument(
        "--till-date",
        default=date.today().isoformat(),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Re-download completed jobs. "
            "Normally do not use this option."
        ),
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    return parser.parse_args()


# ============================================================
# INPUT VALIDATION
# ============================================================

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")

        return list(reader)


def validate_dates(
    from_date: str,
    till_date: str,
) -> None:
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(till_date)

    if start > end:
        raise ValueError(
            "from-date must not be later than till-date"
        )


def validate_inputs(
    universe_rows: list[dict[str, str]],
    board_rows: list[dict[str, str]],
) -> None:
    if not universe_rows:
        raise RuntimeError(
            "Historical common-share universe is empty."
        )

    if not board_rows:
        raise RuntimeError(
            "Historical board history is empty."
        )

    universe_columns = set(universe_rows[0])
    board_columns = set(board_rows[0])

    required_universe = {"SECID"}
    required_board = {
        "SECID",
        "BOARDID",
        "history_from",
        "history_till",
    }

    missing_universe = required_universe - universe_columns
    missing_board = required_board - board_columns

    if missing_universe:
        raise ValueError(
            f"Universe CSV missing columns: {sorted(missing_universe)}"
        )

    if missing_board:
        raise ValueError(
            f"Board history CSV missing columns: {sorted(missing_board)}"
        )

    secids = {
        (row.get("SECID") or "").strip()
        for row in universe_rows
    }

    secids.discard("")

    if not secids:
        raise RuntimeError(
            "No valid SECID values in universe CSV."
        )

    LOG.info(
        "Input universe securities: %s",
        len(secids),
    )

    LOG.info(
        "Input board-history rows: %s",
        len(board_rows),
    )


# ============================================================
# HTTP REQUESTS
# ============================================================

def request_json(
    url: str,
    max_retries: int,
    delay: float,
) -> dict[str, Any]:

    headers = {
        "User-Agent": "Pipeline-MOEX-Raw-Downloader/1.0",
        "Accept": "application/json",
    }

    for attempt in range(max_retries):

        request = urllib.request.Request(
            url,
            headers=headers,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
            ) as response:

                if response.status != 200:
                    raise RuntimeError(
                        f"Unexpected HTTP status: {response.status}"
                    )

                payload = json.loads(
                    response.read().decode("utf-8")
                )

                if not isinstance(payload, dict):
                    raise ValueError(
                        "Invalid MOEX ISS JSON response."
                    )

                time.sleep(delay)

                return payload

        except urllib.error.HTTPError as exc:

            retryable = exc.code in (
                408,
                425,
                429,
                500,
                502,
                503,
                504,
            )

            if not retryable or attempt == max_retries - 1:
                raise

            wait = min(
                120,
                2 ** attempt + random.uniform(0, 1),
            )

            LOG.warning(
                "HTTP %s. Retry in %.1fs.",
                exc.code,
                wait,
            )

            time.sleep(wait)

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            json.JSONDecodeError,
        ) as exc:

            if attempt == max_retries - 1:
                raise

            wait = min(
                120,
                2 ** attempt + random.uniform(0, 1),
            )

            LOG.warning(
                "Request error: %s. Retry in %.1fs.",
                exc,
                wait,
            )

            time.sleep(wait)

    raise RuntimeError(
        f"Request failed after retries: {url}"
    )


# ============================================================
# SQLITE DATABASE
# ============================================================

def create_database(
    connection: sqlite3.Connection,
) -> None:

    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA temp_store=MEMORY")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_bars_raw (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            row_hash TEXT NOT NULL UNIQUE,

            secid TEXT NOT NULL,
            boardid TEXT NOT NULL,
            tradedate TEXT NOT NULL,

            tradingsession INTEGER,
            trade_session_date TEXT,

            shortname TEXT,
            currencyid TEXT,

            numtrades INTEGER,
            value REAL,
            volume REAL,

            open REAL,
            low REAL,
            high REAL,
            legalcloseprice REAL,
            waprice REAL,
            close REAL,

            marketprice2 REAL,
            marketprice3 REAL,
            admittedquote REAL,
            admittedvalue REAL,

            raw_json TEXT NOT NULL,

            downloaded_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        );


        CREATE INDEX IF NOT EXISTS idx_bars_secid_date
        ON daily_bars_raw (secid, tradedate);


        CREATE INDEX IF NOT EXISTS idx_bars_board_date
        ON daily_bars_raw (boardid, tradedate);


        CREATE INDEX IF NOT EXISTS idx_bars_date
        ON daily_bars_raw (tradedate);


        CREATE INDEX IF NOT EXISTS idx_bars_secid_board_date
        ON daily_bars_raw (secid, boardid, tradedate);


        CREATE TABLE IF NOT EXISTS download_jobs (

            secid TEXT NOT NULL,
            boardid TEXT NOT NULL,
            year INTEGER NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',

            next_start INTEGER NOT NULL DEFAULT 0,
            rows_received INTEGER NOT NULL DEFAULT 0,

            error TEXT,

            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (secid, boardid, year)
        );
        """
    )

    connection.commit()


# ============================================================
# BUILD DOWNLOAD JOBS
# ============================================================

def build_board_jobs(
    universe_rows: list[dict[str, str]],
    board_rows: list[dict[str, str]],
    from_date: str,
    till_date: str,
) -> list[dict[str, Any]]:

    secids = {
        (row.get("SECID") or "").strip()
        for row in universe_rows
    }

    secids.discard("")

    board_ranges: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    skipped_boards = Counter()

    for row in board_rows:

        secid = (row.get("SECID") or "").strip()
        board = (row.get("BOARDID") or "").strip()

        if secid not in secids:
            continue

        if board not in ALLOWED_BOARDS:
            continue

        history_from = (
            row.get("history_from") or ""
        ).strip()

        history_till = (
            row.get("history_till") or ""
        ).strip()

        if not history_from or not history_till:
            skipped_boards["missing_history_bounds"] += 1
            continue

        try:
            date.fromisoformat(history_from)
            date.fromisoformat(history_till)
        except ValueError:
            skipped_boards["invalid_history_bounds"] += 1
            LOG.warning(
                "Invalid date bounds: %s/%s: %s - %s",
                secid,
                board,
                history_from,
                history_till,
            )
            continue

        if history_from > history_till:
            skipped_boards["reversed_history_bounds"] += 1
            continue

        key = (secid, board)

        if key not in board_ranges:

            board_ranges[key] = {
                "history_from": history_from,
                "history_till": history_till,
            }

        else:

            current = board_ranges[key]

            current["history_from"] = min(
                current["history_from"],
                history_from,
            )

            current["history_till"] = max(
                current["history_till"],
                history_till,
            )

    jobs = []

    for (secid, board), bounds in sorted(
        board_ranges.items()
    ):

        start_date = max(
            bounds["history_from"],
            from_date,
        )

        end_date = min(
            bounds["history_till"],
            till_date,
        )

        if start_date > end_date:
            continue

        first_year = int(start_date[:4])
        last_year = int(end_date[:4])

        for year in range(
            first_year,
            last_year + 1,
        ):

            chunk_from = max(
                start_date,
                f"{year:04d}-01-01",
            )

            chunk_till = min(
                end_date,
                f"{year:04d}-12-31",
            )

            jobs.append({
                "SECID": secid,
                "BOARDID": board,
                "YEAR": year,
                "FROM_DATE": chunk_from,
                "TILL_DATE": chunk_till,
            })

    LOG.info(
        "Skipped board-history rows: %s",
        dict(skipped_boards),
    )

    return jobs


# ============================================================
# MOEX HISTORY ENDPOINT
# ============================================================

def build_history_url(
    secid: str,
    board: str,
    from_date: str,
    till_date: str,
    start: int,
) -> str:

    params = {
        "from": from_date,
        "till": till_date,
        "start": str(start),
        "limit": str(PAGE_SIZE),
        "iss.meta": "off",
        "iss.only": "history",
    }

    return (
        f"{BASE_URL}/history/engines/stock/markets/shares/"
        f"boards/{urllib.parse.quote(board, safe='')}/"
        f"securities/{urllib.parse.quote(secid, safe='')}.json?"
        f"{urllib.parse.urlencode(params)}"
    )


def parse_history(
    payload: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:

    block = payload.get("history")

    if not isinstance(block, dict):
        raise ValueError(
            "MOEX response has no history block."
        )

    columns = block.get("columns")
    rows = block.get("data")

    if not isinstance(columns, list):
        raise ValueError(
            "Invalid history columns."
        )

    if not isinstance(rows, list):
        raise ValueError(
            "Invalid history data."
        )

    result = []

    for row in rows:

        if len(row) != len(columns):
            raise ValueError(
                "History row length does not match columns."
            )

        result.append(
            dict(zip(columns, row))
        )

    return columns, result


# ============================================================
# TYPE CONVERSION
# ============================================================

def to_float(
    value: Any,
) -> float | None:

    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(
    value: Any,
) -> int | None:

    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# ============================================================
# RAW ROW IDENTITY
# ============================================================

def make_row_hash(
    secid: str,
    board: str,
    row: dict[str, Any],
) -> str:

    payload = {
        "SECID": secid,
        "BOARDID": board,
        "ROW": row,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


# ============================================================
# INSERT RAW DATA
# ============================================================

def insert_history_rows(
    connection: sqlite3.Connection,
    secid: str,
    board: str,
    rows: list[dict[str, Any]],
) -> int:

    inserted_before = connection.total_changes

    sql = """
        INSERT OR IGNORE INTO daily_bars_raw (

            row_hash,

            secid,
            boardid,
            tradedate,

            tradingsession,
            trade_session_date,

            shortname,
            currencyid,

            numtrades,
            value,
            volume,

            open,
            low,
            high,
            legalcloseprice,
            waprice,
            close,

            marketprice2,
            marketprice3,
            admittedquote,
            admittedvalue,

            raw_json
        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """

    values = []

    for row in rows:

        tradedate = row.get("TRADEDATE")

        if not tradedate:
            raise ValueError(
                f"History row has no TRADEDATE: {secid}/{board}"
            )

        row_hash = make_row_hash(
            secid=secid,
            board=board,
            row=row,
        )

        raw_json = json.dumps(
            row,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )

        values.append((
            row_hash,

            secid,
            board,
            str(tradedate),

            to_int(row.get("TRADINGSESSION")),
            row.get("TRADE_SESSION_DATE"),

            row.get("SHORTNAME"),
            row.get("CURRENCYID"),

            to_int(row.get("NUMTRADES")),
            to_float(row.get("VALUE")),
            to_float(row.get("VOLUME")),

            to_float(row.get("OPEN")),
            to_float(row.get("LOW")),
            to_float(row.get("HIGH")),
            to_float(row.get("LEGALCLOSEPRICE")),
            to_float(row.get("WAPRICE")),
            to_float(row.get("CLOSE")),

            to_float(row.get("MARKETPRICE2")),
            to_float(row.get("MARKETPRICE3")),
            to_float(row.get("ADMITTEDQUOTE")),
            to_float(row.get("ADMITTEDVALUE")),

            raw_json,
        ))

    connection.executemany(
        sql,
        values,
    )

    return (
        connection.total_changes - inserted_before
    )


# ============================================================
# JOB CHECKPOINTS
# ============================================================

def get_job_state(
    connection: sqlite3.Connection,
    secid: str,
    board: str,
    year: int,
) -> dict[str, Any] | None:

    row = connection.execute(
        """
        SELECT
            status,
            next_start,
            rows_received
        FROM download_jobs
        WHERE secid = ?
          AND boardid = ?
          AND year = ?
        """,
        (secid, board, year),
    ).fetchone()

    if row is None:
        return None

    return {
        "status": row[0],
        "next_start": row[1],
        "rows_received": row[2],
    }


def save_job_state(
    connection: sqlite3.Connection,
    secid: str,
    board: str,
    year: int,
    status: str,
    next_start: int,
    rows_received: int,
    error: str | None = None,
) -> None:

    connection.execute(
        """
        INSERT INTO download_jobs (
            secid,
            boardid,
            year,
            status,
            next_start,
            rows_received,
            error,
            updated_at
        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
        )

        ON CONFLICT(secid, boardid, year)

        DO UPDATE SET

            status = excluded.status,
            next_start = excluded.next_start,
            rows_received = excluded.rows_received,
            error = excluded.error,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            secid,
            board,
            year,
            status,
            next_start,
            rows_received,
            error,
        ),
    )


# ============================================================
# DOWNLOAD ONE SECURITY / BOARD / YEAR
# ============================================================

def download_job(
    connection: sqlite3.Connection,
    job: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, int]:

    secid = job["SECID"]
    board = job["BOARDID"]
    year = job["YEAR"]

    state = get_job_state(
        connection,
        secid,
        board,
        year,
    )

    if (
        state
        and state["status"] == "complete"
        and not args.refresh
    ):
        return "skipped", 0

    if args.refresh:

        start = 0
        rows_received = 0

    elif state:

        start = int(state["next_start"])
        rows_received = int(state["rows_received"])

    else:

        start = 0
        rows_received = 0

    save_job_state(
        connection,
        secid,
        board,
        year,
        "running",
        start,
        rows_received,
    )

    connection.commit()

    inserted_total = 0

    while True:

        url = build_history_url(
            secid=secid,
            board=board,
            from_date=job["FROM_DATE"],
            till_date=job["TILL_DATE"],
            start=start,
        )

        payload = request_json(
            url=url,
            max_retries=args.max_retries,
            delay=args.delay,
        )

        _, rows = parse_history(payload)

        if not rows:

            save_job_state(
                connection,
                secid,
                board,
                year,
                "complete",
                start,
                rows_received,
            )

            connection.commit()

            break

        inserted = insert_history_rows(
            connection=connection,
            secid=secid,
            board=board,
            rows=rows,
        )

        inserted_total += inserted
        rows_received += len(rows)

        start += len(rows)

        complete = len(rows) < PAGE_SIZE

        save_job_state(
            connection,
            secid,
            board,
            year,
            "complete" if complete else "running",
            start,
            rows_received,
        )

        # Commit every page.
        # A process interruption does not lose completed pages.
        connection.commit()

        LOG.debug(
            "%s/%s/%s | received=%s | inserted=%s | next_start=%s",
            secid,
            board,
            year,
            len(rows),
            inserted,
            start,
        )

        if complete:
            break

    return "complete", inserted_total


# ============================================================
# DATABASE SUMMARY
# ============================================================

def get_database_summary(
    connection: sqlite3.Connection,
) -> dict[str, Any]:

    bar_count = connection.execute(
        "SELECT COUNT(*) FROM daily_bars_raw"
    ).fetchone()[0]

    security_count = connection.execute(
        "SELECT COUNT(DISTINCT secid) FROM daily_bars_raw"
    ).fetchone()[0]

    board_count = connection.execute(
        "SELECT COUNT(DISTINCT boardid) FROM daily_bars_raw"
    ).fetchone()[0]

    date_range = connection.execute(
        """
        SELECT
            MIN(tradedate),
            MAX(tradedate)
        FROM daily_bars_raw
        """
    ).fetchone()

    board_distribution = connection.execute(
        """
        SELECT boardid, COUNT(*)
        FROM daily_bars_raw
        GROUP BY boardid
        ORDER BY boardid
        """
    ).fetchall()

    session_distribution = connection.execute(
        """
        SELECT tradingsession, COUNT(*)
        FROM daily_bars_raw
        GROUP BY tradingsession
        ORDER BY tradingsession
        """
    ).fetchall()

    job_distribution = connection.execute(
        """
        SELECT status, COUNT(*)
        FROM download_jobs
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()

    return {
        "raw_rows": bar_count,
        "unique_secids": security_count,
        "boards": board_count,
        "min_tradedate": date_range[0],
        "max_tradedate": date_range[1],

        "rows_by_board": {
            row[0]: row[1]
            for row in board_distribution
        },

        "rows_by_tradingsession": {
            str(row[0]): row[1]
            for row in session_distribution
        },

        "jobs_by_status": {
            row[0]: row[1]
            for row in job_distribution
        },
    }


# ============================================================
# ATOMIC JSON OUTPUT
# ============================================================

def write_json_atomic(
    path: Path,
    payload: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
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

    temporary.replace(path)


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=(
            "%(asctime)s | %(levelname)s | %(message)s"
        ),
    )

    validate_dates(
        args.from_date,
        args.till_date,
    )

    if args.delay < 0:
        raise ValueError(
            "--delay cannot be negative"
        )

    if args.max_retries < 1:
        raise ValueError(
            "--max-retries must be at least 1"
        )

    universe_path = Path(args.universe_file)
    board_history_path = Path(args.board_history_file)

    universe_rows = read_csv(universe_path)
    board_rows = read_csv(board_history_path)

    validate_inputs(
        universe_rows,
        board_rows,
    )

    jobs = build_board_jobs(
        universe_rows=universe_rows,
        board_rows=board_rows,
        from_date=args.from_date,
        till_date=args.till_date,
    )

    if not jobs:
        raise RuntimeError(
            "No eligible SECID/board/year jobs found."
        )

    db_path = Path(args.db_path)

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_secids = {
        (row.get("SECID") or "").strip()
        for row in universe_rows
    }

    candidate_secids.discard("")

    LOG.info("=" * 65)
    LOG.info("MOEX RAW HISTORY DOWNLOAD")
    LOG.info("=" * 65)

    LOG.info(
        "Candidate securities: %s",
        len(candidate_secids),
    )

    LOG.info(
        "Allowed boards: %s",
        sorted(ALLOWED_BOARDS),
    )

    LOG.info(
        "Requested period: %s - %s",
        args.from_date,
        args.till_date,
    )

    LOG.info(
        "Download jobs: %s",
        len(jobs),
    )

    LOG.info(
        "SQLite database: %s",
        db_path.resolve(),
    )

    counts = Counter()
    inserted_total = 0
    errors = []

    connection = sqlite3.connect(
        db_path,
        timeout=30,
    )

    try:

        create_database(connection)

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            label = (
                f"{job['SECID']}/"
                f"{job['BOARDID']}/"
                f"{job['YEAR']}"
            )

            try:

                status, inserted = download_job(
                    connection=connection,
                    job=job,
                    args=args,
                )

                counts[status] += 1
                inserted_total += inserted

            except Exception as exc:

                error_text = (
                    f"{type(exc).__name__}: {exc}"
                )

                state = get_job_state(
                    connection,
                    job["SECID"],
                    job["BOARDID"],
                    job["YEAR"],
                ) or {}

                save_job_state(
                    connection=connection,
                    secid=job["SECID"],
                    board=job["BOARDID"],
                    year=job["YEAR"],
                    status="error",
                    next_start=int(
                        state.get("next_start", 0)
                    ),
                    rows_received=int(
                        state.get("rows_received", 0)
                    ),
                    error=error_text,
                )

                connection.commit()

                errors.append({
                    "SECID": job["SECID"],
                    "BOARDID": job["BOARDID"],
                    "YEAR": job["YEAR"],
                    "ERROR": error_text,
                })

                counts["error"] += 1

                LOG.exception(
                    "Job failed: %s",
                    label,
                )

            if (
                index % 25 == 0
                or index == len(jobs)
            ):

                LOG.info(
                    "Progress %s/%s | "
                    "complete=%s | skipped=%s | "
                    "errors=%s | inserted=%s",
                    index,
                    len(jobs),
                    counts["complete"],
                    counts["skipped"],
                    counts["error"],
                    inserted_total,
                )

        summary = get_database_summary(
            connection
        )

    finally:
        connection.close()

    # ========================================================
    # OUTPUT REPORTS
    # ========================================================

    output_dir = db_path.parent

    summary["database"] = str(
        db_path.resolve()
    )

    summary["source_universe"] = str(
        universe_path.resolve()
    )

    summary["source_board_history"] = str(
        board_history_path.resolve()
    )

    summary["allowed_boards"] = sorted(
        ALLOWED_BOARDS
    )

    summary["requested_from"] = args.from_date
    summary["requested_till"] = args.till_date

    summary["jobs_total"] = len(jobs)

    summary["jobs_complete_this_run"] = (
        counts["complete"]
    )

    summary["jobs_skipped_this_run"] = (
        counts["skipped"]
    )

    summary["jobs_error_this_run"] = (
        counts["error"]
    )

    summary["new_rows_inserted_this_run"] = (
        inserted_total
    )

    summary["created_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    summary["notes"] = [
        "Raw rows are preserved separately for each board.",
        "No price cleaning or row deletion is performed.",
        "No adjusted prices are calculated in this stage.",
        "Identical raw rows are deduplicated by row_hash.",
        "Different boards and trading sessions remain separate observations.",
        "download_jobs stores resumable progress by security, board and year.",
        "Each downloaded page is committed to SQLite.",
        "history_from/history_till are data availability boundaries, not legal listing dates.",
        "The requested panel period starts in 2005; 2004 is retained as warm-up history.",
    ]

    summary_path = (
        output_dir / "download_summary.json"
    )

    errors_path = (
        output_dir / "download_errors.json"
    )

    write_json_atomic(
        summary_path,
        summary,
    )

    write_json_atomic(
        errors_path,
        errors,
    )

    # ========================================================
    # CONSOLE SUMMARY
    # ========================================================

    print()
    print("=" * 55)
    print("MOEX SQLITE DOWNLOAD")
    print("=" * 55)

    print(
        f"Candidate securities:   {len(candidate_secids)}"
    )

    print(
        f"Download jobs:          {len(jobs)}"
    )

    print(
        f"Jobs completed:         {counts['complete']}"
    )

    print(
        f"Jobs skipped:           {counts['skipped']}"
    )

    print(
        f"Jobs with errors:       {counts['error']}"
    )

    print(
        f"New rows inserted:      {inserted_total:,}"
    )

    print("-" * 55)

    print(
        f"Total raw rows:         {summary['raw_rows']:,}"
    )

    print(
        f"Unique securities:      {summary['unique_secids']}"
    )

    print(
        f"Date range:             "
        f"{summary['min_tradedate']} - "
        f"{summary['max_tradedate']}"
    )

    print(
        f"Boards:                 {summary['rows_by_board']}"
    )

    print("-" * 55)

    print(
        f"SQLite:                 {db_path.resolve()}"
    )

    print(
        f"Summary:                {summary_path.resolve()}"
    )

    print(
        f"Errors:                 {errors_path.resolve()}"
    )

    print("=" * 55)
    print()

    return 1 if errors else 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        raise SystemExit(main())

    except KeyboardInterrupt:

        LOG.warning(
            "Interrupted. Committed pages and job checkpoints "
            "are preserved. Restart the same command to resume."
        )

        raise SystemExit(130)

    except Exception:

        LOG.exception(
            "MOEX raw download failed."
        )

        raise SystemExit(1)
