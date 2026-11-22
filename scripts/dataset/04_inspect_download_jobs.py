
# pipeline/scripts/dataset/04_inspect_download_jobs.py

import sqlite3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "raw" / "moex_daily_raw.sqlite"
OUT = ROOT / "data" / "raw" / "jobs_inspection.json"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

result = {}

# Schema
for table in ["download_jobs", "daily_bars_raw"]:
    cur.execute(f'PRAGMA table_info("{table}")')
    result[f"{table}_schema"] = [
        dict(r) for r in cur.fetchall()
    ]

# Job status distribution
cur.execute("""
    SELECT status, COUNT(*) AS n
    FROM download_jobs
    GROUP BY status
""")
result["status_distribution"] = [
    dict(r) for r in cur.fetchall()
]

# Running jobs
cur.execute("""
    SELECT *
    FROM download_jobs
    WHERE status = 'running'
""")
result["running_jobs"] = [
    dict(r) for r in cur.fetchall()
]

# Failed jobs
cur.execute("""
    SELECT *
    FROM download_jobs
    WHERE status NOT IN ('complete', 'running')
""")
result["non_complete_jobs"] = [
    dict(r) for r in cur.fetchall()
]

# Raw rows per board
cur.execute("""
    SELECT boardid, COUNT(*) AS rows, COUNT(DISTINCT secid) AS securities
    FROM daily_bars_raw
    GROUP BY boardid
    ORDER BY rows DESC
""")
result["board_distribution"] = [
    dict(r) for r in cur.fetchall()
]

# Raw rows per year and board
cur.execute("""
    SELECT substr(tradedate, 1, 4) AS year,
           boardid,
           COUNT(*) AS rows,
           COUNT(DISTINCT secid) AS securities
    FROM daily_bars_raw
    GROUP BY year, boardid
    ORDER BY year, boardid
""")
result["year_board_distribution"] = [
    dict(r) for r in cur.fetchall()
]

# Job counts per board
job_columns = [
    r["name"] for r in
    cur.execute('PRAGMA table_info("download_jobs")').fetchall()
]

if "boardid" in job_columns:
    cur.execute("""
        SELECT boardid, status, COUNT(*) AS n
        FROM download_jobs
        GROUP BY boardid, status
        ORDER BY boardid, status
    """)
    result["jobs_by_board"] = [
        dict(r) for r in cur.fetchall()
    ]

# Check date range of running job, if applicable
cur.execute("""
    SELECT *
    FROM download_jobs
    WHERE status = 'running'
    LIMIT 1
""")
r = cur.fetchone()

if r:
    result["running_job_detail"] = dict(r)

# Save
OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("=" * 60)
print("DOWNLOAD JOB INSPECTION")
print("=" * 60)

print("\nSTATUS:")
for r in result["status_distribution"]:
    print(f"  {r['status']}: {r['n']}")

print("\nRUNNING JOB:")
for r in result["running_jobs"]:
    print(dict(r))

print("\nNON-COMPLETE JOBS:")
for r in result["non_complete_jobs"]:
    print(dict(r))

print("\nBOARD DISTRIBUTION:")
for r in result["board_distribution"]:
    print(dict(r))

print("\nJOBS BY BOARD:")
for r in result.get("jobs_by_board", []):
    print(dict(r))

print("\nREPORT:")
print(OUT)

conn.close()
