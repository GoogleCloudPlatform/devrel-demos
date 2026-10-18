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
Synthetic World Generator for Flow Marketplace Simulation.
Generates enterprises (Kove Bank, Stowe Architects), frontier labs (CenAI, LaprusAI),
realistic diurnal power curves, and compute workload queues including ambiguous/adversarial test cases.
"""

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class ComputeType(str, Enum):
    CPU_STANDARD = "cpu_standard"          # e.g., c2-standard-16
    GPU_H100 = "gpu_h100_80gb"             # e.g., a3-highgpu-8g
    GPU_A100 = "gpu_a100_80gb"             # e.g., a2-ultragpu-1g
    GPU_L4 = "gpu_l4_24gb"                 # e.g., g2-standard-8
    TPU_V5E = "tpu_v5e_8"                  # e.g., v5e-8 pod slice
    TPU_V5P = "tpu_v5p_pod"                # e.g., v5p-8 pod slice
    CONFIDENTIAL_VM = "confidential_vm"    # e.g., n2d-standard with AMD SEV-SNP


class WorkloadRiskCategory(str, Enum):
    BENIGN = "benign"
    UNVETTED_BINARY = "unvetted_binary"
    CROSS_TENANT_ESCAPE = "cross_tenant_escape"
    COMPLIANCE_VIOLATION = "compliance_violation"
    EXFILTRATION_RISK = "exfiltration_risk"
    PRIVILEGED_CONTAINER = "privileged_container"
    AMBIGUOUS_DUAL_USE = "ambiguous_dual_use"
    UNVERIFIED_DEPENDENCY = "unverified_dependency"
    CACHE_PURGE_UNCERTAIN = "cache_purge_uncertain"
    BORDERLINE_EGRESS = "borderline_egress"


@dataclass
class PowerSlot:
    """Represents an idle compute power slot offered by an enterprise."""
    slot_id: str
    seller_id: str
    seller_name: str
    start_hour: int      # 0 to 23
    duration_hours: int
    compute_type: ComputeType
    node_count: int
    total_power_kw: float
    carbon_intensity_g_per_kwh: float  # Grid carbon intensity (g CO2eq / kWh)
    price_per_node_hour_usd: float
    compliance_tags: List[str] = field(default_factory=list)
    available: bool = True

    @property
    def total_energy_kwh(self) -> float:
        return self.total_power_kw * self.duration_hours

    @property
    def end_hour(self) -> int:
        return (self.start_hour + self.duration_hours) % 24


@dataclass
class WorkloadJob:
    """Represents a compute workload submitted by a buyer AI lab."""
    job_id: str
    buyer_id: str
    buyer_name: str
    required_compute: ComputeType
    node_count: int
    estimated_duration_hours: int
    max_price_per_node_hour: float
    target_start_hour: int
    deadline_hour: int
    workload_description: str
    container_image: str
    requested_capabilities: List[str] = field(default_factory=list)
    outbound_destinations: List[str] = field(default_factory=list)
    risk_category: WorkloadRiskCategory = WorkloadRiskCategory.BENIGN
    ground_truth_safe: bool = True
    ground_truth_reason: str = "Standard verified container image."
    risk_tier: int = 1
    risk_level_label: str = "Tier 1: Clearly Benign — Standard Isolated Compute"
    threat_taxonomy: str = "None (Benign)"


@dataclass
class Enterprise:
    """Enterprise seller offering idle overnight compute."""
    enterprise_id: str
    name: str
    industry: str
    primary_timezone: str
    off_peak_start_hour: int  # e.g., 20 (8 PM)
    off_peak_end_hour: int    # e.g., 6 (6 AM)
    base_idle_power_mw: float
    supported_hardware: List[ComputeType]
    security_posture: str
    pci_dss_enforced: bool
    strict_sandbox_required: bool


@dataclass
class FrontierLab:
    """Frontier AI Lab buyer seeking compute during power spikes."""
    lab_id: str
    name: str
    focus: str
    typical_spike_duration_hours: int
    preferred_hardware: List[ComputeType]
    price_tolerance: str  # "high", "medium", "elastic"


class SyntheticWorld:
    """
    Simulation environment modeling enterprises, labs, diurnal power curves,
    and synthetic workload generation.
    """

    def __init__(self, seed: int = 42, stratified_100: bool = True):
        self.seed = seed
        self.stratified_100 = stratified_100
        self.random = random.Random(seed)
        self.enterprises: Dict[str, Enterprise] = self._init_enterprises()
        self.frontier_labs: Dict[str, FrontierLab] = self._init_frontier_labs()

    def _init_enterprises(self) -> Dict[str, Enterprise]:
        return {
            "kove_bank": Enterprise(
                enterprise_id="kove_bank",
                name="Kove Bank",
                industry="Financial Services & Commercial Banking",
                primary_timezone="America/New_York",
                off_peak_start_hour=20,  # 8 PM
                off_peak_end_hour=6,     # 6 AM (10 hours overnight)
                base_idle_power_mw=3.8,  # 3.8 MW overnight idle
                supported_hardware=[
                    ComputeType.CPU_STANDARD,
                    ComputeType.CONFIDENTIAL_VM,
                    ComputeType.GPU_L4,
                    ComputeType.TPU_V5E,
                ],
                security_posture="Ultra-Conservative / Zero-Trust",
                pci_dss_enforced=True,
                strict_sandbox_required=True,
            ),
            "stowe_architects": Enterprise(
                enterprise_id="stowe_architects",
                name="Stowe Architects",
                industry="Global Architectural Design & 3D Visualization",
                primary_timezone="America/Chicago",
                off_peak_start_hour=19,  # 7 PM
                off_peak_end_hour=7,     # 7 AM (12 hours overnight)
                base_idle_power_mw=2.2,  # 2.2 MW idle render cluster
                supported_hardware=[
                    ComputeType.GPU_H100,
                    ComputeType.GPU_A100,
                    ComputeType.GPU_L4,
                    ComputeType.CPU_STANDARD,
                ],
                security_posture="Commercial Enterprise / Standard Container Isolation",
                pci_dss_enforced=False,
                strict_sandbox_required=False,
            ),
        }

    def _init_frontier_labs(self) -> Dict[str, FrontierLab]:
        return {
            "cen_ai": FrontierLab(
                lab_id="cen_ai",
                name="CenAI",
                focus="Autonomous Reasoning & Large-Scale LLM Checkpointing",
                typical_spike_duration_hours=6,
                preferred_hardware=[ComputeType.GPU_H100, ComputeType.GPU_A100, ComputeType.TPU_V5E, ComputeType.TPU_V5P],
                price_tolerance="high",
            ),
            "laprus_ai": FrontierLab(
                lab_id="laprus_ai",
                name="LaprusAI",
                focus="Multimodal Agents & Real-Time Synthetic Data Generation",
                typical_spike_duration_hours=4,
                preferred_hardware=[ComputeType.GPU_L4, ComputeType.CPU_STANDARD],
                price_tolerance="elastic",
            ),
            "deepreason_labs": FrontierLab(
                lab_id="deepreason_labs",
                name="DeepReason Labs",
                focus="Formal Theorem Proving & Code Synthesis Policy Optimization",
                typical_spike_duration_hours=5,
                preferred_hardware=[ComputeType.GPU_A100, ComputeType.CONFIDENTIAL_VM],
                price_tolerance="high",
            ),
            "biofold_frontier": FrontierLab(
                lab_id="biofold_frontier",
                name="BioFold Frontier",
                focus="Macromolecular Structural Folding & Molecular Dynamics",
                typical_spike_duration_hours=6,
                preferred_hardware=[ComputeType.TPU_V5E, ComputeType.GPU_H100],
                price_tolerance="medium",
            ),
        }

    def get_diurnal_idle_power_profile(self, enterprise_id: str, hour: int) -> float:
        """
        Calculates instantaneous idle power (in MW) for an enterprise at a given hour (0-23).
        Models high overnight idle capacity and near-zero daytime idle capacity.
        """
        ent = self.enterprises.get(enterprise_id)
        if not ent:
            return 0.0

        # Peak idle between 1 AM and 4 AM, valley between 10 AM and 4 PM
        # Center peak around 2 AM (hour 2)
        norm_hour = (hour - 2) % 24
        # Cosine curve with peak at norm_hour=0 (2 AM) and trough at norm_hour=12 (2 PM)
        idle_factor = 0.5 * (1 + math.cos(2 * math.pi * norm_hour / 24))
        # Shape it so daytime drops sharply
        idle_factor = math.pow(idle_factor, 1.8)
        return round(ent.base_idle_power_mw * idle_factor, 3)

    def generate_seller_power_slots(self, day: int = 1) -> List[PowerSlot]:
        """
        Generates available idle power slots offered by enterprises.
        Returns 12 balanced slots across all 6 compute types (2 slots per type)
        from Kove Bank and Stowe Architects to ensure reliable, high-liquidity
        matching across all 10 daily buyer workloads.
        """
        from flow.contract_catalog import generate_seller_power_slots as catalog_generate_seller_power_slots
        return catalog_generate_seller_power_slots(day=day)

    def generate_workload_queue(
        self,
        day: int = 1,
        batch_mode: str = "random",
        fixed_size: Optional[int] = None,
        stratified_100: Optional[bool] = None,
    ) -> List[WorkloadJob]:
        """
        Generates buyer workloads from the 100-contract stratified catalog across Days 1–10
        (10 proposals per day in randomized presentation order, 10 proposals per risk tier
        across Risk Tiers 1–10, exact 50 benign / 50 attack split).
        """
        use_stratified = self.stratified_100 if stratified_100 is None else stratified_100
        from flow.contract_catalog import get_workloads_for_day as catalog_get_workloads_for_day
        return catalog_get_workloads_for_day(
            day=day,
            batch_mode=batch_mode,
            fixed_size=fixed_size,
            stratified_100=use_stratified,
            seed=self.seed,
        )

    def generate_stratified_100_batch(self) -> List[WorkloadJob]:
        """
        Returns the full 100-proposal stratified Seed 42 dataset (10 proposals per risk tier
        across Risk Tiers 1–10 = 100 proposals total: 50 benign and 50 attack proposals).
        """
        from flow.contract_catalog import get_stratified_100_batch
        return get_stratified_100_batch(seed=self.seed)
