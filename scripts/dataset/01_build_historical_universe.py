
# Folder: pipeline/scripts/dataset/
# File: 01_build_historical_universe.py
# Purpose: Build historical MOEX universe of common shares.
# Source: MOEX ISS listing history + security metadata.
# Raw API caches and generated files are stored locally, never committed.

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

BASE_URL = "https://iss.moex.com/iss"
DEFAULT_FROM = "1997-03-24"
DEFAULT_OUTPUT = "data/interim/historical_universe"
PAGE_SIZE = 100
MAX_RETRIES = 5
DELAY = 0.15

LOG = logging.getLogger("pipeline_universe")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-date", default=DEFAULT_FROM)
    parser.add_argument("--till-date", default=date.today().isoformat())
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--delay", type=float, default=DELAY)
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES)
    parser.add_argument("--refresh-listing", action="store_true")
    parser.add_argument("--refresh-metadata", action="store_true")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    return parser.parse_args()


def atomic_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def request_json(url: str, retries: int, delay: float):
    headers = {
        "User-Agent": "Pipeline-MOEX-Collector/1.0",
        "Accept": "application/json",
    }

    for attempt in range(retries):
        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))

                if not isinstance(payload, dict):
                    raise ValueError("ISS response is not a JSON object")

                time.sleep(delay)
                return payload

        except urllib.error.HTTPError as exc:
            retryable = exc.code in (
                408, 425, 429, 500, 502, 503, 504
            )

            if not retryable or attempt == retries - 1:
                raise

            wait = min(60, 2 ** attempt + random.random())
            LOG.warning("HTTP %s; retry in %.1fs", exc.code, wait)
            time.sleep(wait)

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            json.JSONDecodeError,
        ) as exc:
            if attempt == retries - 1:
                raise

            wait = min(60, 2 ** attempt + random.random())
            LOG.warning("%s; retry in %.1fs", exc, wait)
            time.sleep(wait)

    raise RuntimeError("Request retry limit exceeded")


def parse_block(payload, name):
    block = payload.get(name)

    if not isinstance(block, dict):
        raise ValueError(f"Missing ISS block: {name}")

    columns = block.get("columns")
    rows = block.get("data")

    if not isinstance(columns, list) or not isinstance(rows, list):
        raise ValueError(f"Malformed ISS block: {name}")

    return columns, rows


def block_dicts(payload, name):
    columns, rows = parse_block(payload, name)
    return [
        dict(zip(columns, row))
        for row in rows
        if len(row) == len(columns)
    ]


def download_listing(args, output_dir):
    cache_dir = output_dir / "listing_pages"
    cache_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    start = 0

    while True:
        cache = cache_dir / f"page_{start:09d}.json"

        if cache.exists() and not args.refresh_listing:
            payload = read_json(cache)
            LOG.info("Listing cache: %s", start)
        else:
            params = urllib.parse.urlencode({
                "from": args.from_date,
                "till": args.till_date,
                "iss.meta": "off",
                "start": start,
                "limit": PAGE_SIZE,
            })

            url = (
                f"{BASE_URL}/history/engines/stock/markets/shares/"
                f"listing.json?{params}"
            )

            LOG.info("Downloading listing page start=%s", start)
            payload = request_json(url, args.max_retries, args.delay)
            atomic_json(cache, payload)

        rows = block_dicts(payload, "securities")

        if not rows:
            break

        all_rows.extend(rows)
        start += len(rows)

        LOG.info("Listing rows accumulated: %s", len(all_rows))

        if len(rows) < PAGE_SIZE:
            break

    if not all_rows:
        raise RuntimeError("MOEX listing returned no rows")

    return all_rows


def get_metadata(secid, cache_dir, args):
    cache = cache_dir / f"{secid}.json"

    if cache.exists() and not args.refresh_metadata:
        payload = read_json(cache)
    else:
        encoded = urllib.parse.quote(secid, safe="")
        params = urllib.parse.urlencode({
            "iss.meta": "off",
            "iss.only": "description",
        })
        url = f"{BASE_URL}/securities/{encoded}.json?{params}"
        payload = request_json(url, args.max_retries, args.delay)
        atomic_json(cache, payload)

    columns, rows = parse_block(payload, "description")
    metadata = {}

    for row in rows:
        if len(row) != len(columns):
            continue

        item = dict(zip(columns, row))
        if item.get("name") is not None:
            metadata[str(item["name"])] = item.get("value")

    return metadata


def write_csv(path, rows, columns=None):
    path.parent.mkdir(parents=True, exist_ok=True)

    if columns is None:
        columns = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)

    tmp = path.with_suffix(path.suffix + ".tmp")

    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    tmp.replace(path)


def main():
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    start_date = date.fromisoformat(args.from_date)
    end_date = date.fromisoformat(args.till_date)

    if start_date > end_date:
        raise ValueError("from-date is later than till-date")

    if args.delay < 0 or args.max_retries < 1:
        raise ValueError("Invalid delay or retry count")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_dir = output_dir / "metadata_cache"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("Universe collection started")
    LOG.info("Range: %s - %s", args.from_date, args.till_date)

    listing_rows = download_listing(args, output_dir)

    # Normalize and aggregate board-level listing rows.
    by_secid = defaultdict(list)
    normalized_listing = []

    for original in listing_rows:
        row = {
            "SECID": original.get("SECID"),
            "SHORTNAME": original.get("SHORTNAME"),
            "NAME": original.get("NAME"),
            "BOARDID": original.get("BOARDID"),
            "decimals": original.get("decimals"),
            "history_from": original.get("history_from"),
            "history_till": original.get("history_till"),
        }

        secid = row["SECID"]
        if secid is None or not str(secid).strip():
            continue

        row["SECID"] = str(secid).strip()
        normalized_listing.append(row)
        by_secid[row["SECID"]].append(row)

    secids = sorted(by_secid)
    master = []
    included = []
    excluded = []
    quarantine = []

    LOG.info("Unique securities: %s", len(secids))

    for i, secid in enumerate(secids, start=1):
        LOG.info("Metadata %s/%s: %s", i, len(secids), secid)

        metadata = None
        error = None

        try:
            metadata = get_metadata(secid, metadata_dir, args)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            LOG.error("Metadata error %s: %s", secid, error)

        security_type = (
            str(metadata.get("TYPE")).strip().lower()
            if metadata and metadata.get("TYPE") is not None
            else None
        )

        if error:
            status, reason = "quarantine", "metadata_request_failed"
        elif not metadata:
            status, reason = "quarantine", "empty_metadata"
        elif not security_type:
            status, reason = "quarantine", "missing_TYPE"
        elif security_type == "common_share":
            status, reason = "included", "TYPE=common_share"
        else:
            status, reason = "excluded", f"TYPE={security_type}"

        board_ids = sorted({
            str(r["BOARDID"])
            for r in by_secid[secid]
            if r.get("BOARDID") is not None
        })

        from_dates = [
            str(r["history_from"])
            for r in by_secid[secid]
            if r.get("history_from")
        ]
        till_dates = [
            str(r["history_till"])
            for r in by_secid[secid]
            if r.get("history_till")
        ]

        row = {
            "SECID": secid,
            "STATUS": status,
            "CLASSIFICATION_REASON": reason,
            "TYPE": metadata.get("TYPE") if metadata else None,
            "GROUP": metadata.get("GROUP") if metadata else None,
            "TYPENAME": metadata.get("TYPENAME") if metadata else None,
            "ISIN": metadata.get("ISIN") if metadata else None,
            "SHORTNAME": metadata.get("SHORTNAME") if metadata else None,
            "NAME": metadata.get("NAME") if metadata else None,
            "BOARD_COUNT": len(board_ids),
            "BOARDS": board_ids,
            "HISTORY_DATA_FROM_MIN": min(from_dates) if from_dates else None,
            "HISTORY_DATA_TILL_MAX": max(till_dates) if till_dates else None,
            "METADATA_ERROR": error,
            "METADATA_JSON": metadata,
        }

        master.append(row)

        if status == "included":
            included.append(row)
        elif status == "excluded":
            excluded.append(row)
        else:
            quarantine.append(row)

        # Periodically checkpoint the master list.
        if i % 25 == 0 or i == len(secids):
            write_csv(output_dir / "security_master_partial.csv", master)
            LOG.info(
                "Checkpoint %s/%s | included=%s | excluded=%s | quarantine=%s",
                i, len(secids), len(included), len(excluded), len(quarantine)
            )

    # Final outputs.
    write_csv(output_dir / "listing_raw.csv", normalized_listing)
    write_csv(output_dir / "security_master.csv", master)
    write_csv(output_dir / "universe_common_shares.csv", included)
    write_csv(output_dir / "universe_exclusions.csv", excluded)
    write_csv(output_dir / "universe_quarantine.csv", quarantine)

    write_csv(
        output_dir / "universe_board_history.csv",
        normalized_listing,
        [
            "SECID", "SHORTNAME", "NAME", "BOARDID",
            "decimals", "history_from", "history_till",
        ],
    )

    summary = {
        "source": f"{BASE_URL}/history/engines/stock/markets/shares/listing",
        "metadata_source": f"{BASE_URL}/securities/{'{SECID}'}",
        "from_date": args.from_date,
        "till_date": args.till_date,
        "listing_board_rows": len(normalized_listing),
        "unique_secids": len(master),
        "common_shares_included": len(included),
        "securities_excluded": len(excluded),
        "securities_quarantined": len(quarantine),
        "classification_policy": {
            "included": "TYPE == common_share",
            "other_types": "excluded",
            "missing_or_failed_metadata": "quarantine",
        },
        "limitations": [
            "history_from/history_till are data availability bounds, not legal listing dates.",
            "Listing catalog membership does not prove daily trading activity.",
            "Historical identity changes and ticker reuse require separate analysis.",
        ],
    }

    atomic_json(output_dir / "universe_summary.json", summary)

    partial = output_dir / "security_master_partial.csv"
    if partial.exists():
        partial.unlink()

    LOG.info("Completed")
    LOG.info("Common shares: %s", len(included))
    LOG.info("Excluded: %s", len(excluded))
    LOG.info("Quarantined: %s", len(quarantine))
    LOG.info("Output: %s", output_dir.resolve())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOG.warning("Interrupted")
        raise SystemExit(130)
    except Exception:
        LOG.exception("Universe build failed")
        raise SystemExit(1)
