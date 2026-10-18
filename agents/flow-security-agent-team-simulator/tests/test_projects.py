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

"""
Unit and integration tests for Flow Projects functionality.
Verifies project creation, isolation across all tabs (Stats, Buyers, Sellers,
Escalations, Console), switching, single-run import into a project, deletion,
and UI rendering.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from flow_cli import FlowAppState, normalize_state_payload, hydrate_state_payload
from flow.ui import render_flow_console_html


class TestFlowProjects(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.projects_file = os.path.join(self.temp_dir.name, "projects_state.json")
        self.state = FlowAppState(seed=42, projects_state_path=self.projects_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_project_initialized_with_baseline_runs(self):
        self.assertEqual(self.state.active_project_id, "default")
        projects = self.state.list_projects()
        self.assertGreaterEqual(len(projects), 1)
        default_proj = next((p for p in projects if p["project_id"] == "default"), None)
        self.assertIsNotNone(default_proj)
        self.assertEqual(default_proj["name"], "Default Project")
        self.assertEqual(default_proj["runs_count"], len(self.state.simulation_runs))
        self.assertGreater(default_proj["runs_count"], 0)
        self.assertEqual(default_proj["contracts_count"], len(self.state.ledger.contracts))
        self.assertEqual(default_proj["slots_count"], len(self.state.slots))

    def test_create_project_starts_empty_and_isolated(self):
        default_runs_count = len(self.state.simulation_runs)
        default_contracts_count = len(self.state.ledger.contracts)
        default_slots_count = len(self.state.slots)

        res = self.state.create_project("Project Alpha", select=True)
        self.assertTrue(res["success"])
        alpha_id = res["active_project_id"]
        self.assertNotEqual(alpha_id, "default")
        self.assertEqual(self.state.active_project_id, alpha_id)

        # Verify new project is completely empty across all tab data stores
        self.assertEqual(len(self.state.simulation_runs), 0)
        self.assertEqual(len(self.state.slots), 0)
        self.assertEqual(len(self.state.ledger.contracts), 0)
        self.assertEqual(len(self.state.escalations.list_pending()), 0)
        self.assertEqual(self.state.current_sim_day, 1)

        # Verify UI payload returned by create_project
        self.assertEqual(res["summary"]["total_slots"], 0)
        self.assertEqual(res["summary"]["total_contracts"], 0)
        self.assertEqual(res["summary"]["pending_escalations"], 0)
        self.assertEqual(len(res["simulation_runs"]), 0)
        self.assertEqual(len(res["slots_data"]), 0)
        self.assertEqual(len(res["contracts_data"]), 0)

        # Verify Default Project still has its original counts in list_projects()
        projects = self.state.list_projects()
        self.assertEqual(len(projects), 2)
        default_meta = next(p for p in projects if p["project_id"] == "default")
        alpha_meta = next(p for p in projects if p["project_id"] == alpha_id)
        self.assertEqual(default_meta["runs_count"], default_runs_count)
        self.assertEqual(default_meta["contracts_count"], default_contracts_count)
        self.assertEqual(default_meta["slots_count"], default_slots_count)
        self.assertEqual(alpha_meta["runs_count"], 0)
        self.assertEqual(alpha_meta["contracts_count"], 0)
        self.assertEqual(alpha_meta["slots_count"], 0)

    def test_add_runs_to_project_and_switch_between_projects(self):
        default_run_indices = [r["run_index"] for r in self.state.simulation_runs]
        default_contract_ids = set(self.state.ledger.contracts.keys())

        # Create Project Alpha and run a 1-day simulation inside it
        created = self.state.create_project("Project Alpha", select=True)
        alpha_id = created["active_project_id"]

        sim_res = self.state.run_simulation(
            days=1,
            team="B",
            seed=42,
            auto_resolve=False,
            reset_existing=False,
            batch_mode="fixed",
            fixed_size=10,
        )
        self.assertTrue(sim_res["success"])
        self.assertEqual(len(self.state.simulation_runs), 1)
        self.assertEqual(self.state.simulation_runs[0]["run_index"], 1)
        self.assertEqual(self.state.simulation_runs[0]["team"], "B")
        alpha_contract_count = len(self.state.ledger.contracts)
        alpha_slot_count = len(self.state.slots)
        self.assertEqual(alpha_contract_count, 10)
        self.assertGreater(alpha_slot_count, 0)

        # Create Project Beta and verify it has 0 runs
        created_beta = self.state.create_project("Project Beta", select=True)
        beta_id = created_beta["active_project_id"]
        self.assertEqual(len(self.state.simulation_runs), 0)
        self.assertEqual(len(self.state.ledger.contracts), 0)
        self.assertEqual(len(self.state.slots), 0)

        # Switch back to Default Project and verify only Default Project runs exist
        sel_default = self.state.select_project("default")
        self.assertTrue(sel_default["success"])
        self.assertEqual(self.state.active_project_id, "default")
        self.assertEqual([r["run_index"] for r in self.state.simulation_runs], default_run_indices)
        self.assertEqual(set(self.state.ledger.contracts.keys()), default_contract_ids)

        # Switch back to Project Alpha and verify its single Team B run is intact
        sel_alpha = self.state.select_project(alpha_id)
        self.assertTrue(sel_alpha["success"])
        self.assertEqual(self.state.active_project_id, alpha_id)
        self.assertEqual(len(self.state.simulation_runs), 1)
        self.assertEqual(self.state.simulation_runs[0]["team"], "B")
        self.assertEqual(len(self.state.ledger.contracts), alpha_contract_count)
        self.assertEqual(len(self.state.slots), alpha_slot_count)

        # Add a second run to Project Alpha
        sim_res2 = self.state.run_simulation(
            days=1,
            team="C",
            seed=42,
            auto_resolve=False,
            reset_existing=False,
            batch_mode="fixed",
            fixed_size=10,
        )
        self.assertTrue(sim_res2["success"])
        self.assertEqual(len(self.state.simulation_runs), 2)
        self.assertEqual([r["team"] for r in self.state.simulation_runs], ["B", "C"])
        self.assertEqual(len(self.state.ledger.contracts), 20)

        # Project Beta must still be empty
        sel_beta = self.state.select_project(beta_id)
        self.assertTrue(sel_beta["success"])
        self.assertEqual(len(self.state.simulation_runs), 0)
        self.assertEqual(len(self.state.ledger.contracts), 0)

    def test_import_single_run_json_into_project(self):
        # Export a single run (Run #1) from Default Project using export_state(run_index=0)
        single_run_export = self.state.export_state(run_index=0)
        run_1_contracts = single_run_export["contracts"]
        run_1_slots = single_run_export["slots"]
        self.assertGreater(len(run_1_contracts), 0)
        self.assertGreater(len(run_1_slots), 0)

        # Create a new project and import the single run into it
        created = self.state.create_project("Imported Runs Project", select=True)
        proj_id = created["active_project_id"]
        self.assertEqual(len(self.state.simulation_runs), 0)

        imp1 = self.state.import_into_project(single_run_export)
        self.assertTrue(imp1["success"])
        self.assertEqual(len(self.state.simulation_runs), 1)
        self.assertEqual(self.state.simulation_runs[0]["run_index"], 1)
        self.assertEqual(len(self.state.ledger.contracts), len(run_1_contracts))
        self.assertEqual(len(self.state.slots), len(run_1_slots))

        # Importing a second time appends as run #2 in this project
        imp2 = self.state.import_into_project(single_run_export)
        self.assertTrue(imp2["success"])
        self.assertEqual(len(self.state.simulation_runs), 2)
        self.assertEqual(self.state.simulation_runs[1]["run_index"], 2)
        self.assertEqual(len(self.state.ledger.contracts), len(run_1_contracts) * 2)

        # Verify project persistence across reload
        reloaded_state = FlowAppState(seed=42, projects_state_path=self.projects_file)
        reloaded_state.select_project(proj_id)
        self.assertEqual(len(reloaded_state.simulation_runs), 2)
        self.assertEqual(len(reloaded_state.ledger.contracts), len(run_1_contracts) * 2)

    def test_delete_project_and_prevent_deleting_default(self):
        created = self.state.create_project("Temp Project", select=True)
        temp_id = created["active_project_id"]
        self.assertEqual(self.state.active_project_id, temp_id)

        # Cannot delete default project
        with self.assertRaises(ValueError):
            self.state.delete_project("default")

        # Delete Temp Project -> falls back to default
        del_res = self.state.delete_project(temp_id)
        self.assertTrue(del_res["success"])
        self.assertEqual(self.state.active_project_id, "default")
        project_ids = [p["project_id"] for p in self.state.list_projects()]
        self.assertNotIn(temp_id, project_ids)
        self.assertIn("default", project_ids)

    def test_ui_renders_projects_and_empty_project_cleanly(self):
        # Create an empty project and render HTML
        self.state.create_project("Empty Workspace", select=True)
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
            simulation_runs=self.state.simulation_runs,
            projects=self.state.list_projects(),
            active_project_id=self.state.active_project_id,
        )
        self.assertIn('id="project-selector"', html)
        self.assertIn('id="btn-new-project"', html)
        self.assertIn('class="modal-overlay" id="new-project-modal"', html)
        self.assertIn("Empty Workspace", html)
        self.assertIn("Default Project", html)
        self.assertIn("function switchProject(", html)
        self.assertIn("function createNewProject(", html)
        self.assertIn("function deleteActiveProject(", html)

        # Verify JS syntax with Node --check
        scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
        self.assertGreater(len(scripts), 0)
        node_bin = shutil.which("node")
        if node_bin:
            for idx, script in enumerate(scripts):
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                    f.write(script)
                    temp_path = f.name
                try:
                    res = subprocess.run([node_bin, "--check", temp_path], capture_output=True, text=True)
                    self.assertEqual(res.returncode, 0, f"JS Syntax Error in script {idx}: {res.stderr}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

    def test_active_project_restored_on_restart(self):
        # Create a custom project and run a simulation inside it
        created = self.state.create_project("Persistent Cloud Project", select=True)
        proj_id = created["active_project_id"]
        self.state.run_simulation(
            days=1,
            team="B",
            seed=42,
            auto_resolve=False,
            reset_existing=False,
            batch_mode="fixed",
            fixed_size=10,
        )
        self.assertEqual(len(self.state.simulation_runs), 1)
        self.assertEqual(len(self.state.ledger.contracts), 10)

        # Simulate container restart pointing at the same projects_state_path
        restarted_state = FlowAppState(seed=42, projects_state_path=self.projects_file)
        self.assertEqual(restarted_state.active_project_id, proj_id)
        self.assertEqual(len(restarted_state.simulation_runs), 1)
        self.assertEqual(restarted_state.simulation_runs[0]["team"], "B")
        self.assertEqual(len(restarted_state.ledger.contracts), 10)

    def test_proposals_collapsed_live_contracts_and_escalations_tab_label(self):
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
            simulation_runs=self.state.simulation_runs,
            projects=self.state.list_projects(),
            active_project_id=self.state.active_project_id,
        )
        # 1. Proposals tab has runs collapsed by default
        self.assertIn("style='cursor:pointer;display:none;'", html)
        self.assertIn("Click to expand", html)
        self.assertIn("EXPANDED_PROPOSAL_RUNS = {}", html)

        # 2. Contracts tab exists and uses 'Contract' column header instead of 'Proposal'
        self.assertIn('id="nav-btn-live-contracts"', html)
        self.assertIn("📜 Contracts", html)
        self.assertIn('id="tab-live-contracts"', html)
        self.assertIn('id="live-contracts-table"', html)
        self.assertIn("<th>Contract</th>", html)
        self.assertIn("function renderLiveContractsTableByRun(", html)

        # 3. Escalations tab button is named '🚨 Escalations' without the count badge
        self.assertIn('id="nav-btn-escalations"', html)
        self.assertIn("🚨 Escalations", html)
        self.assertNotIn("🚨 Human Escalation Queue", html)
        self.assertNotIn('id="pending-counter"', html)

    def test_normalized_schema_round_trip_and_restore(self):
        full_unnorm = self.state.export_state(normalize=False)
        full_norm = self.state.export_state(normalize=True)
        # Verify normalized schema version and catalog keys exist
        self.assertEqual(full_norm.get("schema_normalization"), "v2_normalized")
        self.assertIn("proposal_catalog", full_norm)
        self.assertIn("outcome_catalog", full_norm)
        self.assertNotIn("run", full_norm)
        self.assertNotIn("last_run_data", full_norm)
        # Verify 100% lossless round-trip hydration
        self.assertEqual(hydrate_state_payload(normalize_state_payload(full_unnorm)), full_unnorm)
        # Verify single-run export round-trip
        single_unnorm = self.state.export_state(run_index=0, normalize=False)
        single_norm = normalize_state_payload(single_unnorm)
        self.assertEqual(hydrate_state_payload(single_norm), single_unnorm)
        self.assertLess(len(json.dumps(single_norm)), len(json.dumps(single_unnorm)) * 0.5)

    def test_user_created_run_matches_study_run_metadata_keys(self):
        study_run_keys = set(self.state.simulation_runs[0].keys())
        study_export_keys = set(self.state.export_state(run_index=0, normalize=True).keys())

        created = self.state.create_project("Audit Trail Project", select=True)
        proj_id = created["active_project_id"]

        # 1. Run matching a canonical condition (C01: default Dual Flash Neutral)
        self.state.run_simulation(
            days=1,
            seed=42,
            force_simulation=True,
            batch_mode="fixed",
            fixed_size=10,
        )
        user_run_1 = self.state.simulation_runs[0]
        self.assertEqual(set(user_run_1.keys()), study_run_keys)
        self.assertEqual(user_run_1["condition_id"], "C01")
        self.assertEqual(user_run_1["study_phase"], proj_id)
        self.assertEqual(user_run_1["condition_label"], "Homo-Gemini 3.8 Flash (Neutral -> Neutral)")
        self.assertTrue(user_run_1["team_name"].startswith("[C01] "))

        # 2. Run with non-canonical custom configuration -> U02
        self.state.run_simulation(
            days=1,
            seed=42,
            force_simulation=True,
            batch_mode="fixed",
            fixed_size=10,
            role_rubric_mode="swapped",
        )
        user_run_2 = self.state.simulation_runs[1]
        self.assertEqual(set(user_run_2.keys()), study_run_keys)
        self.assertEqual(user_run_2["condition_id"], "U02")
        self.assertEqual(user_run_2["study_phase"], proj_id)
        self.assertTrue(user_run_2["team_name"].startswith("[U02] "))

        # 3. Single-run normalized export keys match study single-run export keys
        user_export_norm = self.state.export_state(run_index=0, normalize=True)
        self.assertEqual(set(user_export_norm.keys()), study_export_keys)
        self.assertEqual(user_export_norm["condition_id"], "C01")
        self.assertEqual(user_export_norm["study_phase"], proj_id)

    def test_seed_study_projects_when_cache_missing(self):
        seeded_state = FlowAppState(
            seed=42,
            projects_state_path=os.path.join(self.temp_dir.name, "seeded_projects_state.json"),
            seed_study_projects=True,
        )
        proj_names = [p["name"] for p in seeded_state.list_projects()]
        self.assertEqual(proj_names, ["Default Project", "C", "D", "E", "F", "G"])
        for p in seeded_state.list_projects():
            self.assertEqual(p["runs_count"], 18)


if __name__ == "__main__":
    unittest.main()
