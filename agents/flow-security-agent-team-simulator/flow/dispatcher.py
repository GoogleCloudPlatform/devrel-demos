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
The Dispatcher for Flow Marketplace Simulation.
Acts as the agentic matchmaker and traffic cop, routing frontier lab AI workloads
to optimal idle enterprise power slots while minimizing cost and carbon footprint.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from flow.synthetic_world import PowerSlot, WorkloadJob, ComputeType
from flow.ledger import CommitmentLedger, ReservationContract, ReservationStatus


@dataclass
class MatchCandidate:
    """A scored match between a buyer's workload job and a seller's idle power slot."""
    job: WorkloadJob
    slot: PowerSlot
    score: float
    cost_savings_usd: float
    carbon_intensity_g_per_kwh: float
    reasoning: str


class DispatcherEngine:
    """
    Intelligent routing and matchmaking engine for Flow.
    Connects buyer spikes to cheap enterprise off-peak servers.
    """

    def __init__(self, ledger: CommitmentLedger):
        self.ledger = ledger

    def find_matches(
        self,
        available_slots: List[PowerSlot],
        pending_jobs: List[WorkloadJob],
    ) -> List[MatchCandidate]:
        """
        Calculates optimal pairs between workload jobs and idle power slots.
        Filters for hardware compatibility, node count, price tolerance, and timing.
        """
        candidates: List[MatchCandidate] = []
        allocated_slots: set = set()

        # Sort jobs by priority (higher node count or tighter deadline first)
        sorted_jobs = sorted(
            pending_jobs,
            key=lambda j: (j.node_count, -j.estimated_duration_hours),
            reverse=True,
        )

        for job in sorted_jobs:
            best_candidate: Optional[MatchCandidate] = None
            best_score = -1.0

            for slot in available_slots:
                if slot.slot_id in allocated_slots:
                    continue

                is_eligible, reason = self._check_compatibility(slot, job)
                if not is_eligible:
                    continue

                # Compute match score
                score, cost_savings = self._score_match(slot, job)
                if score > best_score:
                    best_score = score
                    best_candidate = MatchCandidate(
                        job=job,
                        slot=slot,
                        score=score,
                        cost_savings_usd=cost_savings,
                        carbon_intensity_g_per_kwh=slot.carbon_intensity_g_per_kwh,
                        reasoning=(
                            f"Matched {job.buyer_name}'s {job.node_count}-node {job.required_compute.value} "
                            f"to {slot.seller_name} ({slot.slot_id}). "
                            f"Savings: ${cost_savings:.2f}, Grid carbon: {slot.carbon_intensity_g_per_kwh} g/kWh. "
                            f"Fit rationale: {reason}"
                        ),
                    )

            if best_candidate:
                candidates.append(best_candidate)
                # If the job consumes most or all nodes, mark slot as allocated
                if best_candidate.job.node_count >= best_candidate.slot.node_count * 0.75:
                    allocated_slots.add(best_candidate.slot.slot_id)

        # Preserve the presentation order of pending_jobs so models evaluate contracts in randomized order
        job_order = {j.job_id: idx for idx, j in enumerate(pending_jobs)}
        candidates.sort(key=lambda c: job_order.get(c.job.job_id, 0))

        return candidates

    def dispatch_match(self, match: MatchCandidate) -> ReservationContract:
        """
        Dispatches a provisional reservation contract into the commitment ledger under SECURITY_HOLD.
        """
        contract = self.ledger.create_security_hold(slot=match.slot, job=match.job)
        return contract

    def _check_compatibility(self, slot: PowerSlot, job: WorkloadJob) -> Tuple[bool, str]:
        """
        Checks hard constraints for matching:
        1. Compute hardware compatibility
        2. Sufficient node count
        3. Duration bounds
        4. Price within buyer budget
        """
        # 1. Hardware match
        if slot.compute_type != job.required_compute:
            return False, f"Hardware mismatch: Slot has {slot.compute_type.value}, Job requires {job.required_compute.value}"

        # 2. Node count
        if slot.node_count < job.node_count:
            return False, f"Insufficient nodes: Slot has {slot.node_count}, Job requires {job.node_count}"

        # 3. Duration
        if slot.duration_hours < job.estimated_duration_hours:
            return False, f"Slot duration ({slot.duration_hours}h) < job duration ({job.estimated_duration_hours}h)"

        # 4. Pricing
        if slot.price_per_node_hour_usd > job.max_price_per_node_hour:
            return False, f"Price exceeds max bid: ${slot.price_per_node_hour_usd} > ${job.max_price_per_node_hour}"

        return True, "Hardware, capacity, duration, and pricing criteria satisfied."

    def _score_match(self, slot: PowerSlot, job: WorkloadJob) -> Tuple[float, float]:
        """
        Scores candidate match (0.0 to 100.0) balancing:
        - Cost discount (50% weight)
        - Low Carbon intensity (30% weight)
        - Capacity utilization efficiency (20% weight)
        """
        # Cost savings per node hour
        price_delta = job.max_price_per_node_hour - slot.price_per_node_hour_usd
        total_savings = price_delta * job.node_count * job.estimated_duration_hours
        cost_score = min(50.0, (price_delta / max(0.01, job.max_price_per_node_hour)) * 50.0)

        # Carbon score (lower is better, baseline 450 g/kWh)
        carbon_score = min(30.0, max(0.0, (450.0 - slot.carbon_intensity_g_per_kwh) / 450.0 * 30.0))

        # Utilization score (matching 16 nodes to 16 nodes is 100% efficient)
        util_ratio = job.node_count / slot.node_count if slot.node_count > 0 else 0.0
        util_score = min(20.0, util_ratio * 20.0)

        total_score = round(cost_score + carbon_score + util_score, 2)
        return total_score, round(total_savings, 2)
