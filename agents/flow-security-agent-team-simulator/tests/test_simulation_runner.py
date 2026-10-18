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
Unit tests for FlowAppState synthetic simulation runner and UI integration.
"""

import unittest
from flow_cli import FlowAppState
from flow.ui import render_flow_console_html


class TestSimulationRunner(unittest.TestCase):
    def setUp(self):
        self.state = FlowAppState(seed=42)

    def test_run_simulation_team_a(self):
        res = self.state.run_simulation(days=1, team="A", seed=42, auto_resolve=False, reset_existing=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["days_simulated"], 1)
        self.assertEqual(res["team"], "A")
        self.assertGreater(len(res["logs"]), 0)
        self.assertIn("summary", res)
        self.assertGreater(res["summary"]["total_slots"], 0)
        self.assertGreater(res["summary"]["total_contracts"], 0)
        self.assertGreater(res["summary"]["total_blocks"], 0)
        self.assertIn("contracts_data", res)
        self.assertIn("pending_escalations", res)

    def test_run_simulation_auto_resolve(self):
        res = self.state.run_simulation(days=1, team="A", seed=42, auto_resolve=True, reset_existing=True)
        self.assertTrue(res["success"])
        # With auto_resolve=True, all deadlocks are resolved
        self.assertEqual(len(self.state.escalations.list_pending()), 0)

    def test_run_simulation_multi_day_append(self):
        res1 = self.state.run_simulation(days=1, team="A", seed=42, auto_resolve=False, reset_existing=True)
        blocks_day1 = res1["ledger_blocks"]

        res2 = self.state.run_simulation(days=1, team="C", seed=42, auto_resolve=False, reset_existing=False)
        blocks_day2 = res2["ledger_blocks"]
        self.assertGreater(blocks_day2, blocks_day1)
        self.assertEqual(res2["team"], "C")

    def test_ui_contains_simulation_elements(self):
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
        )
        self.assertIn("Start Simulation", html)
        self.assertNotIn('id="tabbar-btn-run-sim"', html)
        self.assertNotIn('id="tabbar-btn-last-sim"', html)
        self.assertIn('id="header-btn-run-sim"', html)
        self.assertNotIn('id="header-btn-last-sim"', html)
        self.assertNotIn('Cloud Run Live', html)
        self.assertIn('id="nav-btn-statistics"', html)
        self.assertIn("📊 Stats", html)
        self.assertIn("Last Run Statistics", html)
        self.assertIn("id=\"simulation-modal\"", html)
        self.assertIn("executeSimulation", html)
        self.assertIn("updateAppWithSimulationResults", html)
        self.assertIn("openSimulationModal", html)
        self.assertNotIn('Simulation Data &amp; Marketplace Persistence', html)
        self.assertNotIn('id="stats-drop-card"', html)
        self.assertIn('Download Full Marketplace (.json)', html)
        self.assertIn('Load from JSON File', html)

    def test_ui_slots_and_contracts_have_individual_tabs(self):
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
        )
        self.assertIn('id="nav-btn-slots"', html)
        self.assertIn('id="nav-btn-contracts"', html)
        self.assertIn('switchTab(\'tab-slots\')', html)
        self.assertIn('switchTab(\'tab-contracts\')', html)
        self.assertIn('id="tab-slots"', html)
        self.assertIn('id="tab-contracts"', html)
        # Verify Home tab is the first tab on the left and active by default
        home_btn_pos = html.find('id="nav-btn-home"')
        stats_btn_pos = html.find('id="nav-btn-statistics"')
        contracts_btn_pos = html.find('id="nav-btn-contracts"')
        slots_btn_pos = html.find('id="nav-btn-slots"')
        self.assertGreater(home_btn_pos, 0)
        self.assertLess(home_btn_pos, stats_btn_pos)
        self.assertLess(stats_btn_pos, contracts_btn_pos)
        self.assertLess(contracts_btn_pos, slots_btn_pos)
        self.assertIn('<button class="tab-btn active" onclick="switchTab(\'tab-home\')"', html)
        self.assertIn('<div id="tab-home" class="tab-content active">', html)
        self.assertIn('<div id="tab-statistics" class="tab-content">', html)
        self.assertIn('<div id="tab-contracts" class="tab-content">', html)
        # Verify tab titles
        self.assertIn('🏠 Home', html)
        self.assertIn('📊 Stats', html)
        self.assertIn('📑 Proposals', html)
        self.assertNotIn('📑 Buyers', html)
        self.assertIn('⚡ Sellers', html)
        self.assertIn('💬 Flow Agent', html)
        self.assertIn('🔌 Flow API', html)
        self.assertNotIn('Dynamic Console & Task Inbox', html)
        self.assertNotIn('API & Agent Cards', html)
        self.assertNotIn('Registered Enterprise Off-Peak Power Slots', html)
        self.assertNotIn('Active Digital Reservation Contracts', html)
        # Verify Slot ID is not shown as a column in the table, but present in inspector modal
        self.assertNotIn('<th>Slot ID</th>', html)
        self.assertIn('id="modal-slot-id"', html)
        # Verify column headers
        self.assertIn('<th>Hours Available</th>', html)
        self.assertIn('<th>Price</th>', html)
        self.assertNotIn('<th>Grid Carbon</th>', html)
        self.assertNotIn('<th>Off-Peak Time Window</th>', html)
        self.assertNotIn('<th>Off-Peak Price</th>', html)
        # Verify clean hardware names without parentheses
        self.assertIn('NVIDIA H100 80GB SXM5', html)
        self.assertIn('NVIDIA A100 80GB HBM2e', html)
        self.assertIn('Google Cloud TPU v5e', html)
        self.assertNotIn('NVIDIA H100 80GB SXM5 (NVLink)', html)
        # Verify Best Suited For field in slot inspector modal
        self.assertIn('Best Suited For', html)
        self.assertIn('id="modal-best-suited"', html)
        self.assertIn('Frontier LLM pre-training', html)


    def test_last_run_data_structure_and_simulation(self):
        # Initial state should have preseeded last_run_data
        self.assertIsNotNone(self.state.last_run_data)
        self.assertGreaterEqual(self.state.last_run_data["day"], 1)
        self.assertIn("summary", self.state.last_run_data)
        self.assertIn("workloads", self.state.last_run_data)
        self.assertIn("team_models", self.state.last_run_data)

        # Execute simulation for Team B
        res = self.state.run_simulation(days=1, team="B", seed=101, auto_resolve=False, reset_existing=True)
        self.assertIn("last_run_data", res)
        last_run = res["last_run_data"]
        self.assertEqual(last_run["team"], "B")
        self.assertEqual(last_run["seed"], 101)
        self.assertIn("summary", last_run)
        summary = last_run["summary"]
        self.assertGreater(summary["total_workloads"], 0)
        self.assertGreaterEqual(summary["approved_count"], 0)
        self.assertGreaterEqual(summary["precision"], 0)
        self.assertGreaterEqual(summary["recall"], 0)
        self.assertIn("workloads", last_run)
        self.assertGreater(len(last_run["workloads"]), 0)
        first_wf = last_run["workloads"][0]
        self.assertIn("job_id", first_wf)
        self.assertIn("verdict", first_wf)
        self.assertIn("outcome_type", first_wf)

    def test_ui_renders_last_run_statistics_tab(self):
        res = self.state.run_simulation(days=1, team="A", seed=42, auto_resolve=False, reset_existing=True)
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=res["last_run_data"],
        )
        self.assertIn("id=\"tab-statistics\"", html)
        self.assertIn("Stats", html)
        self.assertIn("sim-runs-table", html)
        self.assertIn("Run &amp; Time (hh:mm)", html)
        self.assertIn("🕒", html)
        self.assertIn("Sensitivity", html)
        self.assertIn("Specificity", html)
        self.assertIn("Council Decision Matrix", html)
        self.assertIn("stat-kpi-total", html)
        self.assertIn("stat-kpi-esc-rate", html)
        self.assertIn("INITIAL_LAST_RUN_DATA", html)
        self.assertIn("renderLastRunStatistics", html)

    def test_intercepted_attacks_includes_escalations(self):
        from flow.security_taskforce import (
            SecurityEvaluation,
            SecurityVerdict,
            OfficerVote,
            OfficerPersonality,
        )
        # Create 1 rejected attack, 1 escalated attack (deadlocked), 1 approved clean
        ev_rejected_attack = SecurityEvaluation(
            contract_id="c_att_rej",
            job_id="job_att_rej",
            team_type="Dynamic Council (gemini-3.8-flash)",
            votes=[OfficerVote("auditor_1", "gemini-3.8-flash", OfficerPersonality.STRICT_COMPLIANCE, SecurityVerdict.REJECTED, 90, "exfiltration", "bad")],
            consensus_verdict=SecurityVerdict.REJECTED,
            is_deadlocked=False,
            escalated_to_human=False,
            summary_reason="Attack detected",
        )
        ev_escalated_attack = SecurityEvaluation(
            contract_id="c_att_esc",
            job_id="job_att_esc",
            team_type="Dynamic Council (gemini-3.8-flash + claude-opus-5)",
            votes=[
                OfficerVote("auditor_1", "gemini-3.8-flash", OfficerPersonality.STRICT_COMPLIANCE, SecurityVerdict.REJECTED, 80, "unverified_dep", "suspicious"),
                OfficerVote("auditor_2", "claude-opus-5", OfficerPersonality.PRAGMATIC_THROUGHPUT, SecurityVerdict.FLAGGED, 50, None, "uncertain"),
            ],
            consensus_verdict=SecurityVerdict.FLAGGED,
            is_deadlocked=True,
            escalated_to_human=True,
            summary_reason="Split decision on attack",
        )
        ev_clean_approved = SecurityEvaluation(
            contract_id="c_clean_app",
            job_id="job_clean_app",
            team_type="Dynamic Council (gemini-3.8-flash)",
            votes=[OfficerVote("auditor_1", "gemini-3.8-flash", OfficerPersonality.STRICT_COMPLIANCE, SecurityVerdict.APPROVED, 10, None, "clean")],
            consensus_verdict=SecurityVerdict.APPROVED,
            is_deadlocked=False,
            escalated_to_human=False,
            summary_reason="Clean workload",
        )

        gt_map = {
            "job_att_rej": False,  # malicious
            "job_att_esc": False,  # malicious
            "job_clean_app": True, # safe
        }

        last_run = self.state.build_last_run_data(
            evaluations=[ev_rejected_attack, ev_escalated_attack, ev_clean_approved],
            ground_truth_map=gt_map,
            dispatch_latencies=[0.005, 0.005, 0.005],
            team_str="D",
            day=3,
        )

        summary = last_run["summary"]
        self.assertEqual(summary["true_positives"], 1)
        self.assertEqual(summary["escalated_attacks"], 1)
        self.assertEqual(summary["intercepted_attacks"], 2)
        self.assertEqual(summary["total_attacks"], 2)
        self.assertEqual(summary["false_negatives"], 0)
        self.assertEqual(summary["intercepted_pct"], 100.0)

        # Check workloads list
        workloads = last_run["workloads"]
        esc_wf = next(w for w in workloads if w["job_id"] == "job_att_esc")
        self.assertEqual(esc_wf["outcome_type"], "ESCALATED_ATTACK")
        self.assertIn("Attack Escalated", esc_wf["outcome_label"])
        self.assertEqual(esc_wf["votes"][0]["officer"], "auditor_1")

    def test_contracts_table_user_friendly_columns(self):
        """Verify the contracts table has the requested user-friendly columns including Ground Truth and Council Assessment."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox, self.state.last_run_data)
        # Verify headers in contracts table
        contracts_start = html.find('id="contracts-table"')
        contracts_end = html.find('</table>', contracts_start)
        contracts_table_html = html[contracts_start:contracts_end]

        self.assertIn("<th>Buyer</th>", contracts_table_html)
        self.assertNotIn("<th>Seller</th>", contracts_table_html)
        self.assertIn("<th>Proposal</th>", contracts_table_html)
        idx_buyer = contracts_table_html.find("<th>Buyer</th>")
        idx_proposal = contracts_table_html.find("<th>Proposal</th>")
        self.assertTrue(idx_buyer < idx_proposal, "Buyer should appear before Proposal")
        self.assertIn("&bull; <span style='color:#cbd5e1;font-weight:500;'>Stowe Architects</span>", contracts_table_html)
        self.assertNotIn("(Seller:", contracts_table_html)
        self.assertNotIn("<th>Parties (Buyer &rarr; Seller)</th>", contracts_table_html)
        self.assertIn("<th>Ground Truth</th>", contracts_table_html)
        self.assertIn("<th>Council Assessment</th>", contracts_table_html)
        self.assertIn("<th>Ledger State</th>", contracts_table_html)
        self.assertIn("<th>Total Cost</th>", contracts_table_html)
        self.assertIn('<th style="text-align:right;">Receipt</th>', contracts_table_html)

        # Verify Ground Truth badges and Council Assessment model & personality details appear (and generic Officer labels are removed)
        self.assertIn("🛡️ Safe", html)
        self.assertIn("⚠️ Attack", html)
        self.assertIn("gemini-3.8-flash", contracts_table_html)
        self.assertTrue(
            "oCeaN (Sentinel)" in contracts_table_html or "Neutral (No Personality)" in contracts_table_html
        )
        self.assertNotIn("Officer 1:", contracts_table_html)
        self.assertNotIn("Officer 2:", contracts_table_html)

        # Verify old cluttering columns are removed from table header
        self.assertNotIn("<th>Contract ID</th>", html)
        self.assertNotIn("<th>Cryptographic SHA-256 Receipt Hash</th>", html)
        self.assertNotIn("<th>Security Resolution Rationale</th>", html)

        # Verify ticket modal has Contract ID and Copy functionality
        self.assertIn('id="receipt-modal-contract-id"', html)
        self.assertIn('id="contract-copy-btn"', html)
        self.assertIn('id="receipt-modal-hash"', html)
        self.assertIn('id="receipt-modal-security"', html)

        # Verify badges and Ledger State column do not wrap
        self.assertIn("white-space: nowrap", html)
        self.assertIn("display: inline-flex", html)
        self.assertIn("#contracts-table td:nth-child(5)", html)
        self.assertIn("white-space:nowrap;min-width:140px;", html)

    def test_security_taskforce_resolution_formatting(self):
        """Verify the Security Taskforce Resolution formatting logic in the UI."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox)

        # Check formatSecurityResolution is present
        self.assertIn("function formatSecurityResolution(raw, dialogue)", html)
        self.assertIn("receipt-modal-security", html)
        self.assertIn("document.getElementById('receipt-modal-security').innerHTML = formatSecurityResolution", html)
        self.assertIn("Initial Council Divergence", html)
        self.assertIn("Deliberation Result & Rationale", html)
        self.assertIn("Multi-Agent Peer Deliberation &amp; Cross-Examination Dialogue", html)
        self.assertIn('"deliberation_dialogue":', html)


    def test_receipt_modal_workload_description(self):
        """Verify workload description is preserved on ReservationContract and rendered in the receipt modal."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox, self.state.last_run_data)

        # Check receipt modal markup has description and container elements
        self.assertIn('id="receipt-modal-description"', html)
        self.assertIn('id="receipt-modal-container"', html)
        self.assertIn("Stated Proposal Description & Intent", html)

        # Check contracts in ledger have workload_description populated
        sample_contract = next((c for c in self.state.ledger.contracts.values() if c.workload_description), None)
        self.assertIsNotNone(sample_contract)
        self.assertGreater(len(sample_contract.workload_description), 10)

        # Check contracts_data_dict has workload_description serialized
        self.assertIn('"workload_description":', html)

    def test_container_manifest_inspector(self):
        """Verify the interactive Container Manifest & Security SBOM drawer in the receipt modal."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox, self.state.last_run_data)

        # Drawer and inspector elements
        self.assertIn('id="btn-inspect-manifest"', html)
        self.assertIn('id="receipt-container-manifest-drawer"', html)
        self.assertIn('id="manifest-base-img"', html)
        self.assertIn('id="manifest-user-ctx"', html)
        self.assertIn('id="manifest-entrypoint"', html)
        self.assertIn('id="manifest-caps-list"', html)
        self.assertIn('id="manifest-egress-list"', html)
        self.assertIn('id="manifest-filetree"', html)
        self.assertIn('id="manifest-scan-summary"', html)

        # JavaScript functions and manifests
        self.assertIn('function toggleContainerManifest()', html)
        self.assertIn('function populateContainerManifest(c)', html)
        self.assertIn('const CONTAINER_MANIFESTS =', html)

        # Check ledger contract attributes
        sample_contract = next((c for c in self.state.ledger.contracts.values() if c.outbound_destinations), None)
        self.assertIsNotNone(sample_contract)
        self.assertIsInstance(sample_contract.requested_capabilities, list)
        self.assertGreater(len(sample_contract.outbound_destinations), 0)

    def test_sellers_page_removed_tier_and_enterprise_selectors(self):
        """Verify that '⚡ Compute Tier:' and '🏛️ Enterprise:' selectors are removed from Sellers tab."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox, self.state.last_run_data)

        # Confirm selectors are removed
        self.assertNotIn("⚡ Compute Tier:", html)
        self.assertNotIn("🏛️ Enterprise:", html)
        self.assertNotIn("class=\"filter-btn tier-filter", html)
        self.assertNotIn("class=\"filter-btn seller-filter", html)

        # Confirm search input and slots table remain
        self.assertIn('id="slots-table"', html)
        self.assertIn('id="slot-search-input"', html)

    def test_escalations_table_and_slideout_modal(self):
        """Verify that the Human Escalation Queue table (grouped by run, without Queue State) and slide-out modal are rendered."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox, self.state.last_run_data)

        # Escalations table structure
        self.assertIn('id="escalations-table"', html)
        self.assertIn('id="escalations-table-body"', html)
        self.assertIn('id="esc-search-input"', html)
        self.assertIn('Deadlock Reason', html)
        self.assertIn('Council Assessment', html)
        self.assertNotIn('<th>Queue State</th>', html)
        self.assertIn('deadlock-reason-clamp', html)
        self.assertIn('-webkit-line-clamp: 4', html)
        self.assertIn('escalation-run-group-header', html)
        self.assertIn('expandAllEscalationRuns()', html)
        self.assertIn('collapseAllEscalationRuns()', html)

        # Escalation slide-out detail modal
        self.assertIn('id="escalation-modal"', html)
        self.assertIn('id="esc-modal-item-id"', html)
        self.assertIn('id="esc-modal-status-badge"', html)
        self.assertIn('id="esc-modal-votes-container"', html)
        self.assertIn('id="esc-modal-delib-container"', html)
        self.assertIn('id="esc-modal-joint-banner"', html)
        self.assertIn('id="esc-modal-action-box"', html)

        # JavaScript functions
        self.assertIn('function inspectEscalation(itemId)', html)
        self.assertIn('function closeEscalationModal()', html)
        self.assertIn('function viewReceiptForCurrentEscalation()', html)
        self.assertIn('function openEscalationForCurrentContract()', html)
        self.assertIn('function applyEscalationFilters()', html)
        self.assertIn('function toggleEscalationRunGroup(runGroup)', html)
        self.assertIn('function renderEscalationsTableByRun(escalationsDataObj)', html)

    def test_security_council_members_custom_configuration(self):
        """Verify the simulation modal features dynamic Security Council Members and deprecated radio buttons are removed."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(self.state.slots, self.state.ledger, self.state.escalations, self.state.inbox, self.state.last_run_data)

        # Deprecated elements must not be present
        self.assertNotIn("🛡️ Security Council Setup", html)
        self.assertNotIn("Neutral Councils — No Personality (Teams E–H)", html)
        self.assertNotIn("Neutral Councils &mdash; No Personality (Teams E–H)", html)
        self.assertNotIn('name="sim-team"', html)

        # New dynamic Security Council Members elements
        self.assertIn("🛡️ Security Council Members", html)
        self.assertIn('id="sim-team-size"', html)
        self.assertIn('id="sim-officers-list"', html)
        self.assertIn('id="sim-officer-row-1"', html)
        self.assertIn('id="sim-officer-row-2"', html)
        self.assertIn('id="sim-officer-row-3"', html)
        self.assertIn('id="sim-officer-model-1"', html)
        self.assertIn('id="sim-officer-personality-1"', html)
        self.assertIn('id="sim-officer-model-2"', html)
        self.assertIn('id="sim-officer-personality-2"', html)
        self.assertIn('id="sim-officer-model-3"', html)
        self.assertIn('id="sim-officer-personality-3"', html)
        self.assertIn('updateSimOfficerRows()', html)

        # Verify simulation execution with custom officers
        res = self.state.run_simulation(
            days=1,
            team="CUSTOM",
            seed=42,
            custom_officers=[
                {"officer_id": "officer_1", "name": "Officer 1", "model_name": "gemini-3.8-flash", "personality": "estj_supervisor"},
                {"officer_id": "officer_2", "name": "Officer 2", "model_name": "claude-opus-5", "personality": "infp_mediator"},
            ]
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["last_run_data"]["team_models"], ["gemini-3.8-flash", "claude-opus-5"])
        self.assertIn("ESTJ (Supervisor)", res["last_run_data"]["team_personalities"])
        self.assertIn("INFP (Mediator)", res["last_run_data"]["team_personalities"])

    def test_escalation_scoping_and_reset_cache(self):
        # 1. Run fresh simulation
        res1 = self.state.run_simulation(days=1, team="A", seed=42, auto_resolve=False, reset_existing=True)
        self.assertTrue(res1["success"])
        self.assertTrue(res1.get("reset_existing"))
        # All pending escalations must belong to contracts in contracts_data
        for esc in res1["pending_escalations"]:
            self.assertIn(esc["contract_id"], res1["contracts_data"])
            self.assertIn(esc["contract_id"], self.state.ledger.contracts)

        # 2. Inject an orphaned escalation pointing to a non-existent contract
        from flow.inbox import EscalationItem
        from flow.security_taskforce import SecurityEvaluation, JointDecision
        orphaned = EscalationItem(
            item_id="esc_orphaned_999",
            contract_id="contract_that_does_not_exist",
            job_id="job_nonexistent",
            buyer_name="Ghost Buyer",
            seller_name="Ghost Seller",
            reason="Orphaned reason",
            evaluation=SecurityEvaluation(
                contract_id="contract_that_does_not_exist",
                job_id="job_nonexistent",
                team_type="Dynamic Council",
                votes=[],
                joint_decision=JointDecision.ESCALATE,
                joint_rationale="Deadlock",
                escalated_to_human=True,
            ),
            queued_at=12345.0,
        )
        self.state.escalations.items["esc_orphaned_999"] = orphaned

        # 3. Running simulation must NOT return the orphaned escalation
        res2 = self.state.run_simulation(days=1, team="A", seed=43, auto_resolve=False, reset_existing=False)
        returned_ids = [e["item_id"] for e in res2["pending_escalations"]]
        self.assertNotIn("esc_orphaned_999", returned_ids)

    def test_ui_escalations_default_pending_filter(self):
        # Verify resolved escalations are excluded from the Escalations tab and ESCALATIONS_DATA
        for item in self.state.escalations.items.values():
            item.resolved = True
            break
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
        )
        # Escalations tab uses expand/collapse run group buttons and excludes resolved items
        self.assertIn('expandAllEscalationRuns()', html)
        self.assertIn('collapseAllEscalationRuns()', html)
        self.assertNotIn('onclick="filterEscalations(', html)
        # updateAppWithSimulationResults should cleanly reset ESCALATIONS_DATA
        self.assertIn("ESCALATIONS_DATA = {};", html)

    def test_simulation_runs_history_and_confusion_matrix_telemetry(self):
        # Run 1
        res1 = self.state.run_simulation(days=1, team="A", seed=42, auto_resolve=False, reset_existing=True)
        self.assertEqual(len(self.state.simulation_runs), 1)
        self.assertEqual(self.state.simulation_runs[0]["run_index"], 1)
        sum1 = self.state.simulation_runs[0]["summary"]
        self.assertIn("sensitivity", sum1)
        self.assertIn("specificity", sum1)
        self.assertIn("total_clean", sum1)
        self.assertGreaterEqual(sum1["sensitivity"], 0.0)
        self.assertLessEqual(sum1["sensitivity"], 100.0)
        self.assertGreaterEqual(sum1["specificity"], 0.0)
        self.assertLessEqual(sum1["specificity"], 100.0)

        # Run 2 with reset_existing=False
        res2 = self.state.run_simulation(days=1, team="D", seed=43, auto_resolve=False, reset_existing=False)
        self.assertEqual(len(self.state.simulation_runs), 2)
        self.assertEqual(self.state.simulation_runs[1]["run_index"], 2)
        self.assertIn("simulation_runs", res2)
        self.assertEqual(len(res2["simulation_runs"]), 2)

        # Verify UI rendering with simulation_runs
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
            simulation_runs=self.state.simulation_runs,
        )
        self.assertIn("sim-runs-table", html)
        self.assertIn("Run #1", html)
        self.assertIn("Run #2", html)
        self.assertIn("Council Decision Matrix", html)
        self.assertIn("id=\"matrix-tp\"", html)
        self.assertIn("id=\"matrix-fn\"", html)
        self.assertIn("id=\"matrix-fp\"", html)
        self.assertIn("id=\"matrix-tn\"", html)
        self.assertIn("id=\"matrix-sensitivity-val\"", html)
        self.assertIn("id=\"matrix-specificity-val\"", html)

        # Run 3 with reset_existing=True resets history
        res3 = self.state.run_simulation(days=1, team="A", seed=44, auto_resolve=False, reset_existing=True)
        self.assertEqual(len(self.state.simulation_runs), 1)
        self.assertEqual(self.state.simulation_runs[0]["run_index"], 1)

    def test_run_stats_modal_encapsulation(self):
        """Verify that run statistics, cognitive personas, and confusion matrix are moved into the 'View Stats' modal, and tab-statistics is a clean table."""
        from flow.ui import render_flow_console_html
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
            simulation_runs=self.state.simulation_runs,
        )

        # 1. run-stats-modal must exist
        self.assertIn('id="run-stats-modal"', html)
        self.assertIn('class="modal-overlay"', html)
        self.assertIn('onclick="closeRunStatsModal()"', html)

        # 2. JS functions must exist
        self.assertIn('function openRunStatsModal(runIdx)', html)
        self.assertIn('function closeRunStatsModal()', html)

        # 3. tab-statistics section must contain the table and NOT the personas or matrix cards directly
        stats_tab_start = html.find('id="tab-statistics"')
        stats_tab_end = html.find('</div>\n\n    <!-- RUN STATISTICS DETAIL MODAL', stats_tab_start)
        if stats_tab_end == -1:
            stats_tab_end = html.find('id="run-stats-modal"', stats_tab_start)
        stats_tab_html = html[stats_tab_start:stats_tab_end]

        self.assertIn('id="sim-runs-table"', stats_tab_html)
        self.assertIn('Simulation Run History', stats_tab_html)
        self.assertNotIn('id="stat-officers-grid"', stats_tab_html)
        self.assertNotIn('id="matrix-tp"', stats_tab_html)
        self.assertNotIn('Council Decision Matrix', stats_tab_html)
        self.assertNotIn('Proposal Evaluation & Consensus Ledger', stats_tab_html)

        # 4. Modal must contain the personas grid and matrix
        modal_start = html.find('id="run-stats-modal"')
        modal_end = html.find('<!-- SIMULATION RUN CONFIGURATION MODAL', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertIn('id="stat-officers-grid"', modal_html)
        self.assertIn('id="matrix-tp"', modal_html)
        self.assertIn('id="matrix-fn"', modal_html)
        self.assertIn('id="matrix-fp"', modal_html)
        self.assertIn('id="matrix-tn"', modal_html)
        self.assertIn('Council Decision Matrix', modal_html)
        self.assertIn('Council Architecture &amp; Cognitive Personas', modal_html)

    def test_rendered_javascript_syntax(self):
        import re
        import shutil
        import subprocess
        import os
        import tempfile

        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
            simulation_runs=self.state.simulation_runs,
        )
        scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
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


    def test_simulation_lock_prevents_reentrant_execution(self):
        self.state._sim_lock.acquire()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                self.state.run_simulation(days=1, team="A", seed=42)
            self.assertIn("already executing", str(ctx.exception))
        finally:
            self.state._sim_lock.release()

    def test_get_genai_client_thread_safety(self):
        import concurrent.futures
        from flow.security_taskforce import SecurityTaskforce
        tf = SecurityTaskforce(self.state.ledger, self.state.world.enterprises)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(tf._get_genai_client) for _ in range(10)]
            results = [f.result() for f in futures]
        # All results should be the exact same instance
        self.assertEqual(len(set(id(r) for r in results)), 1)

    def test_non_randomized_vs_randomized_simulation(self):
        # Non-randomized runs produce identical contract workloads and counts
        state1 = FlowAppState(seed=42)
        res1 = state1.run_simulation(days=1, team="A", reset_existing=True, randomized=False)
        jobs1 = [c["job_id"] for c in res1["contracts_data"].values()]
        safe_count1 = sum(1 for c in res1["contracts_data"].values() if c.get("ground_truth_safe"))

        state2 = FlowAppState(seed=42)
        res2 = state2.run_simulation(days=1, team="A", reset_existing=True, randomized=False)
        jobs2 = [c["job_id"] for c in res2["contracts_data"].values()]
        safe_count2 = sum(1 for c in res2["contracts_data"].values() if c.get("ground_truth_safe"))

        self.assertEqual(jobs1, jobs2)
        self.assertEqual(len(jobs1), len(jobs2))
        self.assertEqual(safe_count1, safe_count2)

    def test_ui_market_horizon_and_batch_toggle(self):
        html = render_flow_console_html(
            self.state.slots,
            self.state.ledger,
            self.state.escalations,
            self.state.inbox,
            last_run_data=self.state.last_run_data,
            simulation_runs=self.state.simulation_runs,
        )
        # Should only have 10 days in sim-horizon
        import re
        horizon_match = re.search(r'<select id="sim-horizon"[^>]*>(.*?)</select>', html, re.DOTALL)
        self.assertIsNotNone(horizon_match)
        horizon_html = horizon_match.group(1)
        self.assertIn('<option value="10" selected>10 days</option>', horizon_html)
        self.assertNotIn('1 week', horizon_html)
        self.assertNotIn('2 weeks', horizon_html)
        self.assertNotIn('1 day', horizon_html)
        self.assertNotIn('3 days', horizon_html)
        self.assertNotIn('4 weeks', horizon_html)

        # Multi-Day Cycle Details was deleted and replaced by fixed / random batch radio buttons without secondary details
        self.assertNotIn('Multi-Day Cycle Details', html)
        self.assertIn('name="sim-batch-mode"', html)
        self.assertIn('value="fixed"', html)
        self.assertIn('value="random"', html)
        self.assertIn('🎯 Fixed-Sized Batch (100)', html)
        self.assertIn('🎲 Random Batch (50–100)', html)
        self.assertNotIn('Deterministic batch (10 workloads/day matching benchmark)', html)
        self.assertNotIn('Dynamic variable-size batch with randomized test counts', html)
        # Deadlock Resolution section was removed and autoResolve is fixed to false
        self.assertNotIn('Deadlock Resolution', html)
        self.assertNotIn('name="sim-deadlock"', html)
        self.assertIn('const autoResolve = false;', html)
        # Execution State Mode titles updated and secondary explanations removed
        self.assertIn('⚡ Append to Simulation', html)
        self.assertNotIn('🎲 New Simulation (Randomized Seed)', html)
        self.assertIn('🔁 New Simulation (Seed 42)', html)
        self.assertNotIn('Append Next Market Day (Dynamic Cycle)', html)
        self.assertNotIn('Fresh Market Simulation (Randomized Seed)', html)
        self.assertNotIn('Deterministic Baseline Reset (Seed 42)', html)
        self.assertNotIn('Advances to next diurnal cycle with fresh proposals', html)
        # Role Assignment Mode has '(Red Flag #4 Control)' removed
        self.assertIn('⚖️ Role Assignment Mode', html)
        self.assertNotIn('Red Flag #4 Control', html)
        # The number/text input for custom batches count was removed
        self.assertNotIn('id="sim-fixed-batch-size"', html)
        self.assertNotIn('Next Day Batch Sizing', html)

    def test_ui_buyers_column_displays_run_id_and_date(self):
        # Create a contract with run_index and timestamp
        state = FlowAppState(seed=42)
        state.run_simulation(days=1, team="A", reset_existing=True, batch_mode="fixed", fixed_size=10)
        html = render_flow_console_html(
            state.slots,
            state.ledger,
            state.escalations,
            state.inbox,
            last_run_data=state.last_run_data,
            simulation_runs=state.simulation_runs,
        )
        # Verify run ID is rendered under buyer name
        self.assertIn("run 1", html)
        # Verify date format YYYY-MM-DD • HH:MM UTC is rendered
        import re
        self.assertTrue(bool(re.search(r'\d{4}-\d{2}-\d{2} • \d{2}:\d{2} UTC', html)))

    def test_append_next_market_day_with_fixed_size_batch(self):
        # Day 1 initial run
        state = FlowAppState(seed=42)
        res1 = state.run_simulation(days=1, team="A", reset_existing=True, batch_mode="fixed", fixed_size=10)
        self.assertTrue(res1["success"])
        initial_contracts_count = len(state.ledger.contracts)

        # Append Day 2 with fixed batch size = 10
        res2 = state.run_simulation(days=1, team="A", reset_existing=False, batch_mode="fixed", fixed_size=10)
        self.assertTrue(res2["success"])
        new_contracts_day2 = len(res2["new_contract_ids"])
        self.assertEqual(new_contracts_day2, 10)
        self.assertEqual(len(state.ledger.contracts), initial_contracts_count + 10)

        # Append Day 3 with fixed batch size = 6
        res3 = state.run_simulation(days=1, team="A", reset_existing=False, batch_mode="fixed", fixed_size=6)
        self.assertTrue(res3["success"])
        new_contracts_day3 = len(res3["new_contract_ids"])
        self.assertEqual(new_contracts_day3, 6)
        self.assertEqual(len(state.ledger.contracts), initial_contracts_count + 10 + 6)

    def test_ocean_32_personas_and_legend_modal(self):
        from flow.security_taskforce import OCEAN_PERSONAS, OfficerPersonality
        from flow_cli import parse_council_spec

        # 1. Verify all 32 Format C OCEAN variations exist and are distinct
        self.assertEqual(len(OCEAN_PERSONAS), 32)
        codes = [p.ocean_code for p in OCEAN_PERSONAS]
        self.assertEqual(len(set(codes)), 32)
        self.assertEqual(codes[0], "ocean")
        self.assertEqual(codes[-1], "OCEAN")

        # 2. Verify case-sensitive parsing preserves Format C distinctions
        p_stoic = OfficerPersonality("ocean")
        p_sentinel = OfficerPersonality("oCeaN")
        p_architect = OfficerPersonality("OCean")
        p_vanguard = OfficerPersonality("OCEAN")
        self.assertNotEqual(p_stoic, p_sentinel)
        self.assertNotEqual(p_sentinel, p_architect)
        self.assertEqual(p_stoic.archetype_name, "Stoic")
        self.assertEqual(p_sentinel.archetype_name, "Sentinel")
        self.assertEqual(p_architect.archetype_name, "Architect")
        self.assertEqual(p_vanguard.archetype_name, "Vanguard")
        self.assertEqual(p_sentinel.short_name, "oCeaN (Sentinel)")
        self.assertIn("Conscientiousness: High", p_sentinel.ocean_traits_summary)
        self.assertIn("Neuroticism/Threat-Vigilance: High", p_sentinel.ocean_traits_summary)

        # 3. Verify CLI parse_council_spec preserves case for OCEAN Format C codes
        council = parse_council_spec("gemini-3.8-flash:oCeaN,claude-opus-5:OCean")
        self.assertEqual(len(council), 2)
        self.assertEqual(OfficerPersonality(council[0]["personality"]), OfficerPersonality.oCeaN)
        self.assertEqual(OfficerPersonality(council[1]["personality"]), OfficerPersonality.OCean)

        # 4. Verify simulation run with OCEAN Format C personas & UI legend modal
        state = FlowAppState(seed=42)
        res = state.run_simulation(
            days=1,
            team="CUSTOM",
            custom_officers=[
                {"officer_id": "officer_1", "name": "Officer 1", "model_name": "gemini-3.8-flash", "personality": "oCeaN"},
                {"officer_id": "officer_2", "name": "Officer 2", "model_name": "gemini-3.8-flash", "personality": "OCean"},
            ],
            reset_existing=True,
            batch_mode="fixed",
            fixed_size=6,
        )
        self.assertTrue(res["success"])
        self.assertIn("oCeaN (Sentinel)", res["last_run_data"]["team_personalities"])
        self.assertIn("OCean (Architect)", res["last_run_data"]["team_personalities"])
        html = render_flow_console_html(
            state.slots,
            state.ledger,
            state.escalations,
            state.inbox,
            last_run_data=state.last_run_data,
            simulation_runs=state.simulation_runs,
        )
        # Verify dropdowns have all 32 OCEAN options + Neutral
        for p in OCEAN_PERSONAS:
            self.assertIn(f'<option value="{p.ocean_code}">{p.short_name}</option>', html)
        # Verify OCEAN Legend modal and buttons exist
        self.assertIn('id="ocean-legend-modal"', html)
        self.assertIn('id="ocean-legend-table"', html)
        self.assertIn('openOceanLegendModal()', html)
        self.assertIn('Big Five (OCEAN) Format C Persona &amp; Archetype Legend', html)

    def test_proposals_grouped_by_run_with_expand_collapse(self):
        state = FlowAppState(seed=42)
        state.run_simulation(days=1, team="BALANCED", reset_existing=True, batch_mode="fixed", fixed_size=4)
        state.run_simulation(days=1, team="SKEPTIC", reset_existing=False, batch_mode="fixed", fixed_size=4)
        html = render_flow_console_html(
            state.slots,
            state.ledger,
            state.escalations,
            state.inbox,
            last_run_data=state.last_run_data,
            simulation_runs=state.simulation_runs,
        )
        self.assertIn("contract-run-group-header", html)
        self.assertIn("id='proposal-run-header-1'", html)
        self.assertIn("id='proposal-run-header-2'", html)
        self.assertIn("toggleProposalRunGroup('1')", html)
        self.assertIn("toggleProposalRunGroup('2')", html)
        self.assertIn("data-run-group='1'", html)
        self.assertIn("data-run-group='2'", html)
        self.assertIn("expandAllProposalRuns()", html)
        self.assertIn("collapseAllProposalRuns()", html)
        self.assertIn("renderContractsTableByRun", html)


if __name__ == "__main__":
    unittest.main()



