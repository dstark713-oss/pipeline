
# pipeline/scripts/dataset/03_check_download_integrity.py

import sqlite3
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "raw" / "moex_daily_raw.sqlite"
OUT_PATH = ROOT / "data" / "raw" / "integrity_check.json"

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    report = {
        "database": str(DB_PATH),
        "tables": {},
        "checks": {},
    }

    # Inspect tables
    tables = [
        r["name"]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    report["tables"]["names"] = tables

    for table in tables:
        columns = cur.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        report["tables"][table] = {
            "columns": [c["name"] for c in columns]
        }

    # Raw bars table
    if "daily_bars_raw" in tables:
        cur.execute("SELECT COUNT(*) FROM daily_bars_raw")
        total_rows = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(DISTINCT secid)
            FROM daily_bars_raw
            """
        )
        unique_securities = cur.fetchone()[0]

        cur.execute(
            """
            SELECT MIN(tradedate), MAX(tradedate)
            FROM daily_bars_raw
            """
        )
        min_date, max_date = cur.fetchone()

        cur.execute(
            """
            SELECT tradedate, COUNT(*)
            FROM daily_bars_raw
            GROUP BY tradedate
            ORDER BY tradedate
            """
        )
        rows_per_date = cur.fetchall()

        cur.execute(
            """
            SELECT substr(tradedate, 1, 4), COUNT(*)
            FROM daily_bars_raw
            GROUP BY substr(tradedate, 1, 4)
            ORDER BY substr(tradedate, 1, 4)
            """
        )
        rows_per_year = cur.fetchall()

        cur.execute(
            """
            SELECT secid, COUNT(*)
            FROM daily_bars_raw
            GROUP BY secid
            ORDER BY COUNT(*) ASC
            LIMIT 20
            """
        )
        least_active = cur.fetchall()

        cur.execute(
            """
            SELECT secid, COUNT(*)
            FROM daily_bars_raw
            GROUP BY secid
            ORDER BY COUNT(*) DESC
            LIMIT 20
            """
        )
        most_active = cur.fetchall()

        report["checks"]["raw_bars"] = {
            "total_rows": total_rows,
            "unique_securities": unique_securities,
            "min_date": min_date,
            "max_date": max_date,
            "rows_per_year": [
                {"year": r[0], "rows": r[1]}
                for r in rows_per_year
            ],
            "rows_per_date_count": len(rows_per_date),
            "least_active_securities": [
                {"secid": r[0], "rows": r[1]}
                for r in least_active
            ],
            "most_active_securities": [
                {"secid": r[0], "rows": r[1]}
                for r in most_active
            ],
        }

    # Download jobs table
    if "download_jobs" in tables:
        job_columns = report["tables"]["download_jobs"]["columns"]

        cur.execute("SELECT COUNT(*) FROM download_jobs")
        total_jobs = cur.fetchone()[0]

        report["checks"]["download_jobs"] = {
            "total_jobs": total_jobs,
            "columns": job_columns,
        }

        # Discover status column
        status_col = next(
            (c for c in job_columns if c.lower() == "status"),
            None
        )

        if status_col:
            cur.execute(
                f"""
                SELECT "{status_col}", COUNT(*)
                FROM download_jobs
                GROUP BY "{status_col}"
                """
            )

            status_counts = {
                str(r[0]): r[1]
                for r in cur.fetchall()
            }

            report["checks"]["download_jobs"]["status_counts"] = (
                status_counts
            )

        # Print unfinished/error jobs if identifiable
        status_col = next(
            (c for c in job_columns if c.lower() == "status"),
            None
        )

        if status_col:
            cur.execute(
                f"""
                SELECT *
                FROM download_jobs
                WHERE LOWER(COALESCE("{status_col}", '')) NOT IN
                ('completed', 'complete', 'done', 'success')
                LIMIT 100
                """
            )

            report["checks"]["download_jobs"]["unfinished_or_failed"] = [
                dict(r) for r in cur.fetchall()
            ]

    # Duplicate check
    if "daily_bars_raw" in tables:
        columns = report["tables"]["daily_bars_raw"]["columns"]

        if "row_hash" in columns:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT row_hash
                    FROM daily_bars_raw
                    GROUP BY row_hash
                    HAVING COUNT(*) > 1
                )
                """
            )
            report["checks"]["raw_bars"]["duplicate_hash_groups"] = (
                cur.fetchone()[0]
            )

    conn.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("SQLITE INTEGRITY AUDIT")
    print("=" * 60)

    print("\nTABLES:")
    for t in tables:
        print(f"  {t}")

    if "raw_bars" in report["checks"]:
        b = report["checks"]["raw_bars"]

        print("\nRAW BARS:")
        print(f"  Rows: {b['total_rows']:,}")
        print(f"  Securities: {b['unique_securities']:,}")
        print(f"  Date range: {b['min_date']} -> {b['max_date']}")

        print("\nROWS PER YEAR:")
        for r in b["rows_per_year"]:
            print(f"  {r['year']}: {r['rows']:,}")

    if "download_jobs" in report["checks"]:
        j = report["checks"]["download_jobs"]

        print("\nDOWNLOAD JOBS:")
        print(f"  Total: {j['total_jobs']:,}")

        if "status_counts" in j:
            for status, count in j["status_counts"].items():
                print(f"  {status}: {count:,}")

        unfinished = j.get("unfinished_or_failed", [])
        print(f"  Unfinished/failed candidates: {len(unfinished)}")

    print("\nREPORT:")
    print(OUT_PATH)

    print("\nAudit completed. Database was not modified.")

if __name__ == "__main__":
    main()
