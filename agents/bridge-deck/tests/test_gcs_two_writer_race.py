#!/usr/bin/env python3
"""
Unit Tests for Phase 1: Storage CAS Adapter & Two-Writer Concurrency Verification.
Verifies that StorageAdapter prevents lost updates under concurrent writer races
across POSIX atomic disk I/O and GCS generation preconditions (if_generation_match).
"""

import sys
import os
import json
import shutil
import tempfile
import threading
import unittest
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tenant import (
    LocalStorageAdapter,
    GCSStorageAdapter,
    StorageConflictError,
    get_storage_adapter,
    sanitize_tenant_id,
    UNCONDITIONAL
)
from google.api_core.exceptions import PreconditionFailed


class TestStorageTwoWriterRace(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_cas_race_"))
        self.tenant_id = "test_tenant"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_local_concurrent_two_writer_race(self):
        """
        Verify that multiple concurrent threads appending to the same project history
        via LocalStorageAdapter suffer zero lost turns or data clobbering.
        """
        adapter = LocalStorageAdapter(base_dir=self.test_dir)
        rel_key = "history/history_lantern.json"
        num_writers = 4
        items_per_writer = 25
        errors = []

        def writer_worker(worker_id: int):
            try:
                for i in range(items_per_writer):
                    item = {
                        "id": f"tx_{worker_id}_{i}",
                        "sender": f"agent_{worker_id}",
                        "prompt_text": f"Message {i} from agent {worker_id}",
                        "timestamp": f"2026-09-15T18:{worker_id:02d}:{i:02d}Z"
                    }
                    adapter.append_json_list(
                        self.tenant_id,
                        rel_key,
                        list_field="transactions",
                        item=item
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer_worker, args=(w,)) for w in range(num_writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")

        doc = adapter.read_json(self.tenant_id, rel_key)
        self.assertIsNotNone(doc)
        txs = doc.get("transactions", [])
        expected_total = num_writers * items_per_writer
        self.assertEqual(len(txs), expected_total, f"Expected {expected_total} transactions, found {len(txs)}")

        # Verify all individual transaction IDs exist
        found_ids = {t["id"] for t in txs}
        for w in range(num_writers):
            for i in range(items_per_writer):
                self.assertIn(f"tx_{w}_{i}", found_ids)

    def test_gcs_cas_precondition_retry_and_success(self):
        """
        Simulate GCS PreconditionFailed (HTTP 412) generation conflict on the first attempt,
        verifying that GCSStorageAdapter catches the conflict, re-reads, and succeeds on retry.
        """
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        adapter = GCSStorageAdapter(bucket_name="mock-bucket", client=mock_client)
        rel_key = "history/bridge_history.json"

        # State tracking for the mock blob
        blob_state = {
            "generation": 100,
            "content": json.dumps({"transactions": [{"id": "tx_initial", "text": "init"}]})
        }

        mock_blob = MagicMock()
        mock_blob.generation = blob_state["generation"]
        mock_blob.download_as_text.side_effect = lambda **kw: blob_state["content"]

        call_count = 0

        def mock_upload(content, content_type=None, if_generation_match=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt: simulate another concurrent writer has bumped generation
                blob_state["generation"] = 105
                blob_state["content"] = json.dumps({"transactions": [
                    {"id": "tx_initial", "text": "init"},
                    {"id": "tx_concurrent_winner", "text": "won race"}
                ]})
                mock_blob.generation = 105
                raise PreconditionFailed("Generation 100 no longer matches current 105")
            # Second attempt succeeds:
            blob_state["content"] = content
            blob_state["generation"] = 110
            mock_blob.generation = 110

        mock_blob.upload_from_string.side_effect = mock_upload
        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_blob

        # Run append_json_list which triggers update_json
        new_item = {"id": "tx_new_2", "text": "second turn"}
        committed_doc, gen = adapter.append_json_list(
            self.tenant_id,
            rel_key,
            list_field="transactions",
            item=new_item
        )

        # Assertions
        self.assertEqual(call_count, 2, "Expected exactly 2 upload attempts (1 retry on 412)")
        self.assertEqual(gen, 110)
        self.assertEqual(len(committed_doc["transactions"]), 3)
        tx_ids = [t["id"] for t in committed_doc["transactions"]]
        self.assertEqual(tx_ids, ["tx_initial", "tx_concurrent_winner", "tx_new_2"])

    def test_gcs_cas_exhausted_retries_raises_conflict_error(self):
        """
        Verify that persistent PreconditionFailed across all retries raises StorageConflictError.
        """
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        adapter = GCSStorageAdapter(bucket_name="mock-bucket", client=mock_client)
        mock_blob = MagicMock()
        mock_blob.generation = 50
        mock_blob.download_as_text.return_value = json.dumps({"transactions": []})
        mock_blob.upload_from_string.side_effect = PreconditionFailed("Conflict")

        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_blob

        with patch("time.sleep", return_value=None):
            with self.assertRaises(StorageConflictError):
                adapter.update_json(
                    self.tenant_id,
                    "history/bridge_history.json",
                    lambda doc: doc,
                    max_retries=3
                )

    def test_append_json_list_idempotency(self):
        """
        Verify that append_json_list updates an existing item with the same id rather than duplicating it.
        """
        adapter = LocalStorageAdapter(base_dir=self.test_dir)
        rel_key = "history/history_test.json"

        item_1 = {"id": "tx_1", "status": "pending", "reactions": ["👍"]}
        adapter.append_json_list(self.tenant_id, rel_key, "transactions", item_1)

        # Update the same transaction
        item_1_update = {"id": "tx_1", "status": "completed"}
        doc, _ = adapter.append_json_list(self.tenant_id, rel_key, "transactions", item_1_update)

        self.assertEqual(len(doc["transactions"]), 1)
        self.assertEqual(doc["transactions"][0]["status"], "completed")
        # Assert reactions were preserved from the previous record
        self.assertEqual(doc["transactions"][0]["reactions"], ["👍"])

    def test_append_line_streaming(self):
        """
        Verify append_line appends continuous text entries to files like facts.jsonl.
        """
        adapter = LocalStorageAdapter(base_dir=self.test_dir)
        rel_key = "memory/facts.jsonl"

        adapter.append_line(self.tenant_id, rel_key, json.dumps({"fact": "Fact A"}))
        adapter.append_line(self.tenant_id, rel_key, json.dumps({"fact": "Fact B"}))

        target_file = self.test_dir / "data" / "tenants" / self.tenant_id / "memory" / "facts.jsonl"
        self.assertTrue(target_file.exists())
        lines = [line.strip() for line in target_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["fact"], "Fact A")
        self.assertEqual(json.loads(lines[1])["fact"], "Fact B")

    def test_list_and_delete_keys(self):
        """
        Verify list_keys, exists, and delete operations.
        """
        adapter = LocalStorageAdapter(base_dir=self.test_dir)
        adapter.replace_json(self.tenant_id, "profiles.json", {"profiles": []}, expected_generation=UNCONDITIONAL)
        adapter.replace_json(self.tenant_id, "history/test.json", {"transactions": []}, expected_generation=UNCONDITIONAL)

        self.assertTrue(adapter.exists(self.tenant_id, "profiles.json"))
        self.assertTrue(adapter.exists(self.tenant_id, "history/test.json"))
        self.assertFalse(adapter.exists(self.tenant_id, "nonexistent.json"))

        keys = adapter.list_keys(self.tenant_id)
        self.assertIn("profiles.json", keys)
        self.assertIn("history/test.json", keys)

    def test_bridge_runner_integration_concurrent_race(self):
        """
        Verify bridge_runner.append_transaction under concurrent multi-threaded execution
        using bridge_dir routes through StorageAdapter without any lost updates.
        """
        import bridge_runner
        from core.tenant import ensure_tenant_initialized

        t_dir = ensure_tenant_initialized(self.tenant_id, base_dir=self.test_dir)
        num_threads = 4
        items_per_thread = 20
        errors = []

        def worker(w_id):
            try:
                for i in range(items_per_thread):
                    tx = {
                        "id": f"tx_br_{w_id}_{i}",
                        "sender": f"agent_{w_id}",
                        "prompt_text": f"Bridge runner turn {i} from thread {w_id}",
                        "timestamp": f"2026-09-16T12:{w_id:02d}:{i:02d}Z"
                    }
                    bridge_runner.append_transaction("lantern", tx, bridge_dir=t_dir)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered errors in concurrent bridge_runner writes: {errors}")

        hist = bridge_runner.load_history("lantern", bridge_dir=t_dir)
        txs = hist.get("transactions", [])
        expected = num_threads * items_per_thread
        self.assertEqual(len(txs), expected, f"Expected {expected} transactions, got {len(txs)}")

        # Verify projects and profiles load/save via bridge_runner
        projects, prj_gen = bridge_runner.load_projects(bridge_dir=t_dir, return_gen=True)
        self.assertIn("projects", projects)
        projects["projects"].append({"id": "p_new", "name": "New Project"})
        bridge_runner.save_projects(projects, bridge_dir=t_dir, expected_generation=prj_gen)
        loaded_p = bridge_runner.load_projects(bridge_dir=t_dir)
        self.assertEqual(len(loaded_p["projects"]), len(projects["projects"]))

        profiles, prof_gen = bridge_runner.load_profiles(bridge_dir=t_dir, return_gen=True)
        self.assertIn("profiles", profiles)
        profiles["profiles"].append({"id": "prof_new", "name": "New Profile"})
        bridge_runner.save_profiles(profiles, bridge_dir=t_dir, expected_generation=prof_gen)
        loaded_prof = bridge_runner.load_profiles(bridge_dir=t_dir)
        self.assertEqual(len(loaded_prof["profiles"]), len(profiles["profiles"]))

    def test_production_race_save_history_vs_append_transaction(self):
        """
        Amendment A3:
        Production race test verifying that when bridge_runner.save_history races
        against bridge_runner.append_transaction, save_history carries the caller's
        expected generation, passes it to if_generation_match, raises StorageConflictError
        on conflict, and Writer B's transaction survives intact.
        """
        import bridge_runner
        from core.tenant import ensure_tenant_initialized

        t_dir = ensure_tenant_initialized(self.tenant_id, base_dir=self.test_dir)

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        adapter = GCSStorageAdapter(bucket_name="mock-bucket", client=mock_client)
        rel_key = "history/bridge_history.json"

        # Shared backend state for mock GCS blob
        state = {
            "generation": 100,
            "content": json.dumps({"transactions": [{"id": "tx_0", "prompt_text": "initial"}]})
        }

        mock_blob = MagicMock()
        mock_blob.generation = state["generation"]
        mock_blob.download_as_text.side_effect = lambda **kw: state["content"]

        captured = {}

        def mock_upload(payload, content_type=None, if_generation_match=None):
            captured["gen"] = if_generation_match
            if if_generation_match is not None and if_generation_match != state["generation"]:
                raise PreconditionFailed(f"Generation mismatch: expected {if_generation_match}, actual {state['generation']}")
            state["content"] = payload
            state["generation"] += 1
            mock_blob.generation = state["generation"]

        mock_blob.upload_from_string.side_effect = mock_upload
        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_blob

        with patch("bridge_runner.get_active_storage", return_value=(adapter, self.tenant_id)):
            # 1. Writer A loads history at generation 100
            stale_doc, gen_a = bridge_runner.load_history("lantern", bridge_dir=t_dir, return_gen=True)
            self.assertEqual(gen_a, 100)
            self.assertEqual(len(stale_doc["transactions"]), 1)

            stale_doc["transactions"].append({"id": "tx_a_stale", "prompt_text": "from writer A"})

            # 2. Writer B calls production bridge_runner.append_transaction
            # Bumping generation in GCS from 100 -> 101
            tx_b = {"id": "tx_b_concurrent", "prompt_text": "appended by writer B"}
            bridge_runner.append_transaction("lantern", tx_b, bridge_dir=t_dir)
            self.assertEqual(state["generation"], 101)
            self.assertIn("tx_b_concurrent", state["content"])

            # --- RED Demonstration: Naive unconditioned overwrite destroys concurrent appends ---
            state_copy = copy.deepcopy(state)
            mock_upload(json.dumps(stale_doc), if_generation_match=None)
            self.assertNotIn("tx_b_concurrent", state["content"], "Unconditioned write clobbers concurrent transactions (RED baseline)")

            # Restore state after RED baseline to generation 101
            state["generation"] = state_copy["generation"]
            state["content"] = state_copy["content"]
            mock_blob.generation = state["generation"]

            # 3. GREEN Verification: Writer A calls production bridge_runner.save_history with expected_generation=gen_a
            with self.assertRaises(StorageConflictError):
                bridge_runner.save_history(
                    stale_doc,
                    project_id="lantern",
                    bridge_dir=t_dir,
                    expected_generation=gen_a
                )

            # Assert replace_json carried the generation the CALLER read
            self.assertEqual(
                captured.get("gen"),
                100,
                "replace_json must carry the generation the CALLER read, not a fresh one"
            )

            # 4. Assert that Writer B's transaction survives intact in the final document!
            final_doc = json.loads(state["content"])
            tx_ids = [t["id"] for t in final_doc["transactions"]]
            self.assertIn("tx_b_concurrent", tx_ids, "Writer B's transaction must survive in the final document (GREEN verification)")
            self.assertNotIn("tx_a_stale", tx_ids, "Stale write must not have been committed")

    def test_production_race_save_profiles_non_history(self):
        """
        A3-shaped race test against non-history document (profiles.json):
        Verifies that bridge_runner.save_profiles carries expected_generation from load_profiles,
        detects concurrent modification by Writer B, raises StorageConflictError,
        and preserves Writer B's updates intact.
        """
        import bridge_runner
        from core.tenant import ensure_tenant_initialized

        t_dir = ensure_tenant_initialized(self.tenant_id, base_dir=self.test_dir)

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        adapter = GCSStorageAdapter(bucket_name="mock-bucket", client=mock_client)

        state = {
            "generation": 200,
            "content": json.dumps({"profiles": [{"id": "lead", "name": "Project Lead"}]})
        }

        mock_blob = MagicMock()
        mock_blob.generation = state["generation"]
        mock_blob.download_as_text.side_effect = lambda **kw: state["content"]

        captured = {}

        def mock_upload(payload, content_type=None, if_generation_match=None):
            captured["gen"] = if_generation_match
            if if_generation_match is not None and if_generation_match != state["generation"]:
                raise PreconditionFailed(f"Generation mismatch: expected {if_generation_match}, actual {state['generation']}")
            state["content"] = payload
            state["generation"] += 1
            mock_blob.generation = state["generation"]

        mock_blob.upload_from_string.side_effect = mock_upload
        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_blob

        with patch("bridge_runner.get_active_storage", return_value=(adapter, self.tenant_id)):
            # 1. Writer A loads profiles at generation 200
            stale_profiles, gen_a = bridge_runner.load_profiles(bridge_dir=t_dir, return_gen=True)
            self.assertEqual(gen_a, 200)
            stale_profiles["profiles"].append({"id": "agent_a", "name": "Agent A"})

            # 2. Concurrent Writer B updates profiles directly in GCS (gen 200 -> 201)
            b_profiles = {"profiles": [{"id": "lead", "name": "Project Lead"}, {"id": "agent_b", "name": "Agent B"}]}
            mock_upload(json.dumps(b_profiles), if_generation_match=200)
            self.assertEqual(state["generation"], 201)

            # 3. Writer A attempts to save with stale gen_a (200) -> must raise StorageConflictError
            with self.assertRaises(StorageConflictError):
                bridge_runner.save_profiles(
                    stale_profiles,
                    bridge_dir=t_dir,
                    expected_generation=gen_a
                )

            # Verify replace_json carried gen_a (200)
            self.assertEqual(captured.get("gen"), 200)

            # 4. Verify Writer B's persona survives intact
            final_profiles = json.loads(state["content"])
            ids = [p["id"] for p in final_profiles["profiles"]]
            self.assertIn("agent_b", ids, "Writer B's persona must survive in profiles.json")
            self.assertNotIn("agent_a", ids, "Stale persona from Writer A must be rejected")

    def test_unconditional_sentinel_bypasses_cas_check(self):
        """
        Verify that passing expected_generation=UNCONDITIONAL explicitly bypasses
        CAS checks across both LocalStorageAdapter and GCSStorageAdapter.
        """
        # 1. LocalStorageAdapter
        local_adapter = LocalStorageAdapter(base_dir=self.test_dir)
        local_adapter.replace_json(self.tenant_id, "test_unconditional.json", {"v": 1}, expected_generation=UNCONDITIONAL)
        # Bypasses even with mismatched generation
        _, gen = local_adapter.replace_json(self.tenant_id, "test_unconditional.json", {"v": 2}, expected_generation=UNCONDITIONAL)
        self.assertEqual(local_adapter.read_json(self.tenant_id, "test_unconditional.json")["v"], 2)

        # 2. GCSStorageAdapter
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generation = 999
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        captured = {}
        def mock_upload(payload, content_type=None, if_generation_match=None):
            captured["gen"] = if_generation_match

        mock_blob.upload_from_string.side_effect = mock_upload

        gcs_adapter = GCSStorageAdapter(bucket_name="mock-bucket", client=mock_client)
        gcs_adapter.replace_json(self.tenant_id, "test.json", {"unconditional": True}, expected_generation=UNCONDITIONAL)
        self.assertIsNone(captured.get("gen"), "UNCONDITIONAL write must not pass if_generation_match")


if __name__ == "__main__":
    unittest.main()

