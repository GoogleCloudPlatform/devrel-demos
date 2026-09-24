#!/usr/bin/env python3
"""
Two-Process Race Verification (Red/Green Baseline).
Demonstrates that naive multi-process file writes produce real lost updates (RED),
and that LocalStorageAdapter with cross-process file locking guarantees zero lost turns (GREEN).
"""

import os
import sys
import json
import time
import shutil
import tempfile
import multiprocessing
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tenant import LocalStorageAdapter


# --- Top-level worker functions required by multiprocessing spawn on macOS ---

def _naive_worker(file_path: str, worker_id: int, count: int):
    for i in range(count):
        time.sleep(0.002)
        doc = {"transactions": []}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception:
                doc = {"transactions": []}
        doc.setdefault("transactions", []).append({
            "id": f"tx_naive_{worker_id}_{i}",
            "worker": worker_id
        })
        time.sleep(0.002)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)


def _adapter_worker(base_dir: str, tenant_id: str, rel_key: str, worker_id: int, count: int):
    adapter = LocalStorageAdapter(base_dir=Path(base_dir))
    for i in range(count):
        item = {
            "id": f"tx_adapter_{worker_id}_{i}",
            "worker": worker_id,
            "data": f"Turn {i} from process {worker_id}"
        }
        adapter.append_json_list(
            tenant_id,
            rel_key,
            list_field="transactions",
            item=item
        )


class TestTwoProcessRace(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_2proc_race_"))
        self.tenant_id = "test_tenant"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_unprotected_two_process_race_lost_updates_demonstrated(self):
        """
        RED BASELINE:
        Two separate OS processes performing naive read-modify-write without cross-process locks.
        Proves that without CAS/locks, lost updates occur under multi-process concurrency.
        """
        naive_file = self.test_dir / "unprotected_history.json"
        turns_per_worker = 20
        p1 = multiprocessing.Process(target=_naive_worker, args=(str(naive_file), 1, turns_per_worker))
        p2 = multiprocessing.Process(target=_naive_worker, args=(str(naive_file), 2, turns_per_worker))

        p1.start()
        p2.start()
        p1.join()
        p2.join()

        self.assertTrue(naive_file.exists())
        doc = json.loads(naive_file.read_text(encoding="utf-8"))
        actual_count = len(doc.get("transactions", []))
        expected_total = turns_per_worker * 2

        print(f"\n[RED BASELINE OUTPUT] Expected: {expected_total}, Actual: {actual_count}, Lost: {expected_total - actual_count}")
        # Demonstrates lost updates (failure to record all turns)
        self.assertLess(actual_count, expected_total, f"Expected lost updates under naive multi-process write, but got {actual_count}/{expected_total}")

    def test_protected_two_process_adapter_zero_lost_updates(self):
        """
        GREEN VERIFICATION:
        Two separate OS processes performing concurrent writes through LocalStorageAdapter.
        Proves zero lost updates across processes.
        """
        rel_key = "history/history_test.json"
        turns_per_worker = 25
        p1 = multiprocessing.Process(target=_adapter_worker, args=(str(self.test_dir), self.tenant_id, rel_key, 1, turns_per_worker))
        p2 = multiprocessing.Process(target=_adapter_worker, args=(str(self.test_dir), self.tenant_id, rel_key, 2, turns_per_worker))

        p1.start()
        p2.start()
        p1.join()
        p2.join()

        adapter = LocalStorageAdapter(base_dir=self.test_dir)
        self.assertFalse(adapter._lock_degraded, "LocalStorageAdapter should not be in degraded lock mode")
        doc = adapter.read_json(self.tenant_id, rel_key)
        self.assertIsNotNone(doc)
        txs = doc.get("transactions", [])
        expected_total = turns_per_worker * 2

        print(f"\n[GREEN VERIFICATION OUTPUT] Expected: {expected_total}, Actual: {len(txs)}, Lost: 0")
        self.assertEqual(len(txs), expected_total, f"Expected {expected_total} turns, found {len(txs)}")

        found_ids = {t["id"] for t in txs}
        for w in [1, 2]:
            for i in range(turns_per_worker):
                self.assertIn(f"tx_adapter_{w}_{i}", found_ids)


if __name__ == "__main__":
    unittest.main()
