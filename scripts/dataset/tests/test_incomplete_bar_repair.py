from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "06_repair_incomplete_bars.py"
SPEC = importlib.util.spec_from_file_location("repair_incomplete_bars_tested", SCRIPT)
repair = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(repair)


class IncompleteBarRepairTests(unittest.TestCase):
    def test_normalize_complete_candle(self):
        candle = {
            "begin": "2024-01-10 10:00:00",
            "end": "2024-01-10 18:50:00",
            "interval": 24,
            "open": 100,
            "high": 112,
            "low": 98,
            "close": 108,
            "volume": 1000,
            "value": 108000,
        }
        result = repair.normalize_candle(candle)
        self.assertIsNotNone(result)
        self.assertEqual(result["tradedate"], "2024-01-10")
        self.assertEqual(result["close"], 108.0)

    def test_reject_incomplete_or_invalid_candle(self):
        incomplete = {"begin": "2024-01-10", "open": 100, "high": 110, "low": 90}
        invalid = {
            "begin": "2024-01-10", "open": 100, "high": 90,
            "low": 95, "close": 96,
        }
        self.assertIsNone(repair.normalize_candle(incomplete))
        self.assertIsNone(repair.normalize_candle(invalid))

    def test_candidate_selection_is_grouped_by_board_security_date(self):
        connection = sqlite3.connect(":memory:")
        connection.execute(
            """
            CREATE TABLE daily_bars_raw (
                row_hash TEXT, secid TEXT, boardid TEXT, tradedate TEXT,
                open REAL, high REAL, low REAL, close REAL
            )
            """
        )
        connection.executemany(
            "INSERT INTO daily_bars_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("a", "AAA", "TQBR", "2024-01-10", 10, 12, 9, None),
                ("b", "AAA", "TQBR", "2024-01-10", 10, 12, 9, None),
                ("c", "BBB", "EQBR", "2024-01-11", None, None, None, None),
                ("d", "CCC", "TQBR", "2024-01-12", 10, 12, 9, 11),
            ],
        )
        result = repair.find_incomplete_keys(connection)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["source_rows"], 2)
        self.assertEqual(set(result[0]["original_row_hashes"].split(",")), {"a", "b"})
        connection.close()

    def test_overlay_upsert_is_idempotent_and_preserves_original_hashes(self):
        connection = sqlite3.connect(":memory:")
        repair.create_overlay(connection)
        key = {
            "secid": "AAA", "boardid": "TQBR", "tradedate": "2024-01-10",
            "original_row_hashes": "raw-hash-1,raw-hash-2",
        }
        candle = {
            "open": 100.0, "high": 110.0, "low": 95.0,
            "close": 105.0, "volume": 1000.0, "value": 105000.0,
            "begin": "2024-01-10 10:00:00", "end": "2024-01-10 18:50:00",
            "interval": 24,
        }
        self.assertTrue(repair.upsert_repair(connection, key, candle))
        self.assertFalse(repair.upsert_repair(connection, key, candle))
        row = connection.execute(
            "SELECT original_row_hashes, close FROM repaired_bars"
        ).fetchone()
        self.assertEqual(row, ("raw-hash-1,raw-hash-2", 105.0))
        connection.close()


if __name__ == "__main__":
    unittest.main()
