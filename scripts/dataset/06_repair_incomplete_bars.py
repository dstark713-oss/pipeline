from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import sqlite3
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DB = PROJECT_ROOT / "data" / "raw" / "moex_daily_raw.sqlite"
OVERLAY_DB = PROJECT_ROOT / "data" / "interim" / "bar_repairs" / "moex_candle_repairs.sqlite"
REPORT_PATH = PROJECT_ROOT / "data" / "interim" / "bar_repairs" / "repair_report.json"
REFRESH_MODULE_PATH = PROJECT_ROOT / "scripts" / "dataset" / "fresh" / "refresh_pipeline.py"
DOWNLOADER_PATH = PROJECT_ROOT / "scripts" / "dataset" / "02_download_daily_bars_sqlite.py"

OHLC_FIELDS = ("open", "high", "low", "close")
REPAIR_FIELDS = ("open", "high", "low", "close", "volume", "value")
ALLOWED_BOARDS = ("TQBR", "EQBR")
REQUEST_DELAY_SECONDS = 0.25
MAX_RETRIES = 5
PAGE_SIZE = 100

LOG = logging.getLogger("pipeline.repair_incomplete_bars")


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def sqlite_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30)
    connection.execute("PRAGMA query_only=ON")
    return connection


def create_overlay(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS repaired_bars (
            secid TEXT NOT NULL,
            boardid TEXT NOT NULL,
            tradedate TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL,
            value REAL,
            source_endpoint TEXT NOT NULL,
            source_begin TEXT,
            source_end TEXT,
            source_interval INTEGER,
            original_row_hashes TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            repair_id TEXT NOT NULL UNIQUE,
            fetched_at_utc TEXT NOT NULL,
            PRIMARY KEY (secid, boardid, tradedate)
        )
        """
    )
    connection.commit()


def find_incomplete_keys(raw: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = {
        row[1].lower()
        for row in raw.execute("PRAGMA table_info(daily_bars_raw)")
    }
    required = {"secid", "boardid", "tradedate", *OHLC_FIELDS}
    missing = required - columns
    if missing:
        raise RuntimeError(f"daily_bars_raw missing columns: {sorted(missing)}")

    rows = raw.execute(
        """
        SELECT
            secid, boardid, tradedate,
            GROUP_CONCAT(row_hash),
            COUNT(*) AS source_rows
        FROM daily_bars_raw
        WHERE boardid IN ('TQBR', 'EQBR')
          AND (
              open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
          )
        GROUP BY secid, boardid, tradedate
        ORDER BY tradedate, secid, boardid
        """
    ).fetchall()

    return [
        {
            "secid": str(row[0]).strip().upper(),
            "boardid": str(row[1]).strip().upper(),
            "tradedate": str(row[2])[:10],
            "original_row_hashes": row[3] or "",
            "source_rows": int(row[4]),
        }
        for row in rows
    ]


def normalize_candle(candle: dict[str, Any]) -> dict[str, Any] | None:
    def number(value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    begin = candle.get("begin")
    if not begin:
        return None

    result = {
        "tradedate": str(begin)[:10],
        "open": number(candle.get("open")),
        "high": number(candle.get("high")),
        "low": number(candle.get("low")),
        "close": number(candle.get("close")),
        "volume": number(candle.get("volume")),
        "value": number(candle.get("value")),
        "begin": str(begin),
        "end": str(candle.get("end")) if candle.get("end") is not None else None,
        "interval": int(candle["interval"]) if candle.get("interval") is not None else None,
    }

    if any(result[field] is None for field in OHLC_FIELDS):
        return None

    o, h, l, c = (result[field] for field in OHLC_FIELDS)
    if min(o, h, l, c) <= 0 or h < l or h < max(o, c) or l > min(o, c):
        return None

    return result


def build_repair_id(secid: str, board: str, tradedate: str, candle: dict[str, Any]) -> str:
    payload = json.dumps(
        [secid, board, tradedate, [candle.get(field) for field in REPAIR_FIELDS]],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def upsert_repair(
    overlay: sqlite3.Connection,
    key: dict[str, Any],
    candle: dict[str, Any],
) -> bool:
    repair_id = build_repair_id(
        key["secid"], key["boardid"], key["tradedate"], candle
    )
    existing = overlay.execute(
        """
        SELECT repair_id FROM repaired_bars
        WHERE secid=? AND boardid=? AND tradedate=?
        """,
        (key["secid"], key["boardid"], key["tradedate"]),
    ).fetchone()
    if existing and existing[0] == repair_id:
        return False

    overlay.execute(
        """
        INSERT INTO repaired_bars (
            secid, boardid, tradedate, open, high, low, close,
            volume, value, source_endpoint, source_begin, source_end,
            source_interval, original_row_hashes, payload_json,
            repair_id, fetched_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(secid, boardid, tradedate) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low,
            close=excluded.close, volume=excluded.volume, value=excluded.value,
            source_endpoint=excluded.source_endpoint,
            source_begin=excluded.source_begin, source_end=excluded.source_end,
            source_interval=excluded.source_interval,
            original_row_hashes=excluded.original_row_hashes,
            payload_json=excluded.payload_json,
            repair_id=excluded.repair_id,
            fetched_at_utc=excluded.fetched_at_utc
        """,
        (
            key["secid"], key["boardid"], key["tradedate"],
            candle["open"], candle["high"], candle["low"], candle["close"],
            candle["volume"], candle["value"],
            "MOEX ISS /candles.json", candle["begin"], candle["end"],
            candle["interval"], key["original_row_hashes"],
            json.dumps(candle, ensure_ascii=False, sort_keys=True, default=str),
            repair_id, datetime.now(timezone.utc).isoformat(),
        ),
    )
    overlay.commit()
    return True


def run_repair(dry_run: bool = False, limit: int | None = None) -> dict[str, Any]:
    if not RAW_DB.is_file():
        raise FileNotFoundError(f"Raw database not found: {RAW_DB}")

    refresh = load_module("pipeline_refresh_for_repair", REFRESH_MODULE_PATH)
    downloader_module = load_module("pipeline_raw_downloader_for_repair", DOWNLOADER_PATH)
    downloader = downloader_module

    OVERLAY_DB.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    raw = sqlite_readonly(RAW_DB)
    overlay = sqlite3.connect(OVERLAY_DB, timeout=30)
    create_overlay(overlay)

    counts = {
        "candidate_keys": 0,
        "fetched_candles": 0,
        "repaired": 0,
        "unchanged": 0,
        "no_candle_returned": 0,
        "incomplete_or_invalid_candle": 0,
        "errors": 0,
    }
    errors: list[dict[str, str]] = []

    try:
        keys = find_incomplete_keys(raw)
        if limit is not None:
            keys = keys[:limit]
        counts["candidate_keys"] = len(keys)

        for index, key in enumerate(keys, start=1):
            try:
                url = refresh.build_candles_url(
                    secid=key["secid"],
                    board=key["boardid"],
                    from_date=key["tradedate"],
                    till_date=key["tradedate"],
                    start=0,
                )
                payload = downloader.request_json(
                    url=url,
                    max_retries=MAX_RETRIES,
                    delay=REQUEST_DELAY_SECONDS,
                )
                candles = refresh.parse_candles(payload)
                counts["fetched_candles"] += len(candles)

                matching = [
                    normalize_candle(candle)
                    for candle in candles
                    if str(candle.get("begin", ""))[:10] == key["tradedate"]
                ]
                matching = [item for item in matching if item is not None]

                if not matching:
                    if candles:
                        counts["incomplete_or_invalid_candle"] += 1
                    else:
                        counts["no_candle_returned"] += 1
                    continue

                # One daily candle is expected for a SECID/board/date key.
                if len(matching) != 1:
                    raise RuntimeError(
                        f"Expected one daily candle, received {len(matching)}"
                    )

                if dry_run:
                    counts["repaired"] += 1
                elif upsert_repair(overlay, key, matching[0]):
                    counts["repaired"] += 1
                else:
                    counts["unchanged"] += 1

            except Exception as exc:
                counts["errors"] += 1
                errors.append({
                    "secid": key["secid"],
                    "boardid": key["boardid"],
                    "tradedate": key["tradedate"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
                LOG.exception(
                    "Repair failed for %s/%s/%s",
                    key["secid"], key["boardid"], key["tradedate"],
                )

            if index % 50 == 0 or index == len(keys):
                LOG.info("Progress %d/%d | %s", index, len(keys), counts)
            time.sleep(REQUEST_DELAY_SECONDS)

        report = {
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "raw_database": str(RAW_DB),
            "raw_database_opened_read_only": True,
            "overlay_database": str(OVERLAY_DB),
            "dry_run": dry_run,
            "selection": "raw rows with at least one NULL OHLC field on TQBR/EQBR",
            "source": "MOEX ISS daily candles endpoint",
            "counts": counts,
            "errors": errors,
            "raw_database_modified": False,
        }
        REPORT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report
    finally:
        raw.close()
        overlay.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair incomplete raw daily bars into a separate overlay SQLite database."
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate candidates without writing repairs.")
    parser.add_argument("--limit", type=int, default=None, help="Limit candidate keys for a small test run.")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    run_repair(dry_run=args.dry_run, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
