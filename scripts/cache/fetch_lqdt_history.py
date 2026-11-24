from __future__ import annotations

"""Download LQDT daily bars into a local cache, never into the research dataset.

Run from repository root:
    python scripts/cache/fetch_lqdt_history.py
Optional:
    python scripts/cache/fetch_lqdt_history.py --from-date 2018-01-01
    python scripts/cache/fetch_lqdt_history.py --output data/cache/lqdt_daily.csv
"""

import argparse
import csv
import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE_URL = "https://iss.moex.com/iss"
SECID = "LQDT"
BOARD = "TQTF"
PAGE_SIZE = 100
LOG = logging.getLogger("pipeline.lqdt_cache")


def request_json(url: str, retries: int = 5) -> dict:
    headers = {"User-Agent": "pipeline-lqdt-cache/1.0", "Accept": "application/json"}
    for attempt in range(retries):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("MOEX ISS returned a non-object JSON payload")
                return payload
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 425, 429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
        wait = min(60, 2 ** attempt + random.random())
        LOG.warning("Request failed; retrying in %.1fs", wait)
        time.sleep(wait)
    raise RuntimeError("MOEX ISS request failed after retries")


def fetch_history(start_date: str, end_date: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        params = {
            "from": start_date,
            "till": end_date,
            "start": str(offset),
            "limit": str(PAGE_SIZE),
            "iss.meta": "off",
            "iss.only": "history",
            "history.columns": "TRADEDATE,OPEN,CLOSE",
        }
        url = (
            f"{BASE_URL}/history/engines/stock/markets/shares/"
            f"boards/{BOARD}/securities/{SECID}.json?"
            f"{urllib.parse.urlencode(params)}"
        )
        payload = request_json(url)
        block = payload.get("history")
        if not isinstance(block, dict) or not isinstance(block.get("columns"), list) or not isinstance(block.get("data"), list):
            raise ValueError("Unexpected MOEX ISS history response structure")
        columns = block["columns"]
        page = [dict(zip(columns, row)) for row in block["data"]]
        rows.extend(page)
        LOG.info("Fetched page: %d rows; total=%d", len(page), len(rows))
        if len(page) < PAGE_SIZE:
            break
        offset += len(page)
        time.sleep(0.20)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache LQDT daily OHLC observations from MOEX ISS.")
    parser.add_argument("--from-date", default="2018-01-01")
    parser.add_argument("--till-date", default=(date.today() - timedelta(days=1)).isoformat())
    parser.add_argument("--output", type=Path, default=Path("data/cache/lqdt_daily.csv"))
    args = parser.parse_args()

    date.fromisoformat(args.from_date)
    date.fromisoformat(args.till_date)
    if args.from_date > args.till_date:
        raise ValueError("--from-date must not be later than --till-date")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raw = fetch_history(args.from_date, args.till_date)
    normalized = {}
    for row in raw:
        tradedate = row.get("TRADEDATE")
        open_price = row.get("OPEN")
        close_price = row.get("CLOSE")
        if not tradedate or open_price in (None, "") or close_price in (None, ""):
            continue
        normalized[str(tradedate)] = {
            "tradedate": str(tradedate),
            "open": float(open_price),
            "close": float(close_price),
        }

    if not normalized:
        raise RuntimeError(
            f"No usable {SECID}/{BOARD} observations returned. "
            "Check the MOEX instrument board and ISS response."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = args.output.with_suffix(args.output.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["tradedate", "open", "close"])
        writer.writeheader()
        writer.writerows(normalized[key] for key in sorted(normalized))
    temp_path.replace(args.output)

    dates = sorted(normalized)
    print(f"Instrument: {SECID}, board: {BOARD}")
    print(f"Rows cached: {len(dates):,}")
    print(f"Date range: {dates[0]} .. {dates[-1]}")
    print(f"Cache: {args.output.resolve()}")
    print("This file is local cache only; it is not added to the canonical dataset.")


if __name__ == "__main__":
    main()
