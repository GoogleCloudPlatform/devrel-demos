# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from flow.security_taskforce import (
    DEFAULT_HEADLESS_COUNCIL,
    OfficerPersonality,
    SecurityTaskforce,
)
from flow_cli import parse_council_spec, FlowAppState


class TestFlowCLI(unittest.TestCase):
    def test_parse_council_spec_default(self):
        officers = parse_council_spec(None)
        self.assertEqual(len(officers), 2)
        self.assertEqual(officers[0]["model_name"], "gemini-3.8-flash")
        self.assertEqual(officers[0]["personality"], OfficerPersonality.NEUTRAL)
        self.assertEqual(officers[1]["model_name"], "gemini-3.8-flash")
        self.assertEqual(officers[1]["personality"], OfficerPersonality.NEUTRAL)

        # Empty string also returns default
        officers_empty = parse_council_spec("")
        self.assertEqual(len(officers_empty), 2)

    def test_parse_council_spec_2_officers(self):
        spec = "gemini-3.8-flash:estj,claude-opus-5:infp"
        officers = parse_council_spec(spec)
        self.assertEqual(len(officers), 2)
        self.assertEqual(officers[0]["model_name"], "gemini-3.8-flash")
        self.assertEqual(officers[0]["personality"], OfficerPersonality.ESTJ)
        self.assertEqual(officers[1]["model_name"], "claude-opus-5")
        self.assertEqual(officers[1]["personality"], OfficerPersonality.INFP)

    def test_parse_council_spec_3_officers(self):
        spec = "gemini-3.8-flash:neutral,claude-sonnet-5:istp,openai/gpt-oss-120b-maas:neutral"
        officers = parse_council_spec(spec)
        self.assertEqual(len(officers), 3)
        self.assertEqual(officers[0]["model_name"], "gemini-3.8-flash")
        self.assertEqual(officers[1]["model_name"], "claude-sonnet-5")
        self.assertEqual(officers[2]["model_name"], "openai/gpt-oss-120b-maas")

    def test_parse_council_spec_invalid_size(self):
        with self.assertRaises(ValueError):
            parse_council_spec("gemini-3.8-flash:neutral")

        with self.assertRaises(ValueError):
            parse_council_spec("m1:neutral,m2:neutral,m3:neutral,m4:neutral")

    def test_simulation_run_with_dynamic_council(self):
        state = FlowAppState(seed=42)
        council = [
            {"officer_id": "o1", "name": "Officer 1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "o2", "name": "Officer 2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
        ]
        result = state.run_simulation(
            days=1,
            seed=42,
            custom_officers=council,
            force_simulation=True,
        )
        self.assertIn("summary", result)
        self.assertIn("last_run_data", result)
        last_run = result["last_run_data"]
        self.assertIn("workloads", last_run)
        self.assertEqual(last_run["team_models"], ["gemini-3.8-flash", "claude-opus-5"])
        self.assertEqual(last_run["team_name"], "[C03] 2-Officer Council (Gemini 3.8 Flash + Claude Opus 5)")
        self.assertEqual(last_run["condition_id"], "C03")
        self.assertEqual(last_run["study_phase"], "default")
        self.assertEqual(last_run["condition_label"], "Golden Pair: Gemini 3.8 Flash -> Claude Opus 5")
        self.assertTrue(len(last_run["workloads"]) > 0)

    def test_baseline_state_preloaded_on_startup(self):
        state = FlowAppState(seed=42)
        self.assertGreaterEqual(len(state.slots), 120)
        self.assertGreaterEqual(len(state.ledger.contracts), 1800)
        self.assertGreaterEqual(len(state.ledger.receipts), 3600)
        self.assertGreaterEqual(len(state.escalations.items), 110)
        self.assertEqual(len(state.simulation_runs), 18)
        self.assertGreaterEqual(state.current_sim_day, 10)
        self.assertTrue(state.ledger.verify_audit_trail())

    def test_save_state_roundtrip(self):
        import tempfile, os
        state = FlowAppState(seed=42)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = os.path.join(tmpdir, "test_state.json")
            saved_path = state.save_state_to_file(tmpfile)
            self.assertTrue(os.path.exists(saved_path))
            
            # Create a blank state and load from tmpfile
            new_state = FlowAppState(seed=42, preseed=False)
            loaded = new_state.load_preseed_data(tmpfile)
            self.assertTrue(loaded)
            self.assertGreaterEqual(len(new_state.slots), 120)
            self.assertGreaterEqual(len(new_state.ledger.contracts), 624)
            self.assertTrue(new_state.ledger.verify_audit_trail())


    def test_export_full_state_and_single_run(self):
        state = FlowAppState(seed=42)
        # Test full marketplace export
        full_export = state.export_state()
        self.assertEqual(full_export["type"], "flow_simulation_full_export")
        self.assertGreaterEqual(len(full_export["slots"]), 120)
        self.assertGreaterEqual(len(full_export["contracts"]), 624)
        self.assertGreaterEqual(len(full_export["receipts"]), 1248)
        self.assertGreaterEqual(len(full_export["simulation_runs"]), 5)

        # Test single run export
        run_export = state.export_state(run_index=0)
        self.assertEqual(run_export["type"], "flow_simulation_run_export")
        self.assertEqual(run_export["run_index"], 0)
        self.assertEqual(run_export["run_number"], 1)
        self.assertIn("workloads", run_export)
        self.assertGreater(len(run_export["workloads"]), 0)

    def test_restore_state_repopulates_app(self):
        state = FlowAppState(seed=42)
        full_export = state.export_state()
        
        # Restore into a fresh blank state
        new_state = FlowAppState(seed=999, preseed=False)
        self.assertEqual(len(new_state.ledger.contracts), 0)
        
        res = new_state.restore_state(full_export, save_as_baseline=False)
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(len(new_state.slots), 120)
        self.assertGreaterEqual(len(new_state.ledger.contracts), 624)
        self.assertGreaterEqual(len(new_state.ledger.receipts), 1248)
        self.assertGreaterEqual(len(new_state.escalations.items), 110)
        self.assertEqual(len(new_state.simulation_runs), len(full_export["simulation_runs"]))
        self.assertTrue(new_state.ledger.verify_audit_trail())

    def test_simulation_deterministic_vs_randomized_mode(self):
        state = FlowAppState(seed=42)
        res_det = state.run_simulation(days=1, team="A", reset_existing=True, randomized=False)
        self.assertFalse(res_det["randomized"])
        self.assertEqual(res_det["seed_used"], 42)

        res_rand = state.run_simulation(days=1, team="A", reset_existing=True, randomized=True)
        self.assertTrue(res_rand["randomized"])
        self.assertNotEqual(res_rand["seed_used"], 0)


if __name__ == "__main__":
    unittest.main()
