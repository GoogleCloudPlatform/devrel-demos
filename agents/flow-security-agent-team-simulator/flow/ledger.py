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
Commitment Ledger for Flow Marketplace Simulation.
A digital reservation system and cryptographic receipt book for enterprise idle power.
Tracks leases, reservations, and state transitions with SHA-256 tamper-evident chaining.
"""

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from flow.synthetic_world import PowerSlot, WorkloadJob


class ReservationStatus(str, Enum):
    REQUESTED = "requested"
    SECURITY_HOLD = "security_hold"
    COMMITTED = "committed"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class LeaseOffer:
    """An enterprise seller's offered compute lease."""
    offer_id: str
    seller_id: str
    seller_name: str
    slot_id: str
    compute_type: str
    node_count: int
    start_hour: int
    duration_hours: int
    price_per_node_hour_usd: float
    carbon_intensity_g_per_kwh: float
    total_power_kw: float
    created_at: float = field(default_factory=time.time)
    active: bool = True


@dataclass
class WorkloadBid:
    """A frontier lab's compute bid."""
    bid_id: str
    buyer_id: str
    buyer_name: str
    job_id: str
    required_compute: str
    node_count: int
    duration_hours: int
    max_price_per_node_hour: float
    target_start_hour: int
    created_at: float = field(default_factory=time.time)


@dataclass
class LedgerReceipt:
    """
    Cryptographic digital receipt issued for every state change in the commitment ledger.
    Forms an auditable SHA-256 merkle-like receipt chain.
    """
    receipt_id: str
    contract_id: str
    action: str  # "HOLD_PLACED", "SECURITY_APPROVED", "SECURITY_REJECTED", "COMMITTED", "ESCALATED", "SETTLED"
    seller_id: str
    buyer_id: str
    node_count: int
    duration_hours: int
    total_energy_kwh: float
    estimated_cost_usd: float
    carbon_saved_kg: float
    timestamp: float
    previous_receipt_hash: str
    receipt_hash: str = ""

    def calculate_hash(self) -> str:
        payload = (
            f"{self.receipt_id}:{self.contract_id}:{self.action}:"
            f"{self.seller_id}:{self.buyer_id}:{self.node_count}:"
            f"{self.duration_hours}:{self.total_energy_kwh:.4f}:"
            f"{self.estimated_cost_usd:.4f}:{self.carbon_saved_kg:.4f}:"
            f"{self.timestamp:.4f}:{self.previous_receipt_hash}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ReservationContract:
    """A binding digital reservation contract between Seller and Buyer."""
    contract_id: str
    offer_id: str
    slot_id: str
    job_id: str
    seller_id: str
    seller_name: str
    buyer_id: str
    buyer_name: str
    compute_type: str
    node_count: int
    start_hour: int
    duration_hours: int
    agreed_price_per_node_hour: float
    total_power_kw: float
    status: ReservationStatus
    created_at: float = field(default_factory=time.time)
    security_verdict: Optional[str] = None
    security_reason: Optional[str] = None
    receipt_ids: List[str] = field(default_factory=list)
    workload_description: str = ""
    container_image: str = ""
    requested_capabilities: List[str] = field(default_factory=list)
    outbound_destinations: List[str] = field(default_factory=list)
    risk_category: str = "benign"
    risk_tier: int = 1
    risk_level_label: str = "Tier 1: Clearly Benign — Standard Isolated Compute"
    threat_taxonomy: str = "None (Benign)"
    ground_truth_safe: bool = True
    run_index: Optional[int] = None
    run_timestamp: Optional[str] = None

    @property
    def total_energy_kwh(self) -> float:
        return self.total_power_kw * self.duration_hours

    @property
    def total_cost_usd(self) -> float:
        return round(self.node_count * self.agreed_price_per_node_hour * self.duration_hours, 2)


class CommitmentLedger:
    """
    Thread-safe digital commitment ledger and receipt book.
    Maintains active leases, reservation state machine, and tamper-evident audit receipts.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self._lock = threading.RLock()
        self.offers: Dict[str, LeaseOffer] = {}
        self.contracts: Dict[str, ReservationContract] = {}
        self.receipts: List[LedgerReceipt] = []
        self._last_receipt_hash: str = self.GENESIS_HASH

    def register_power_slot(self, slot: PowerSlot) -> LeaseOffer:
        """Publishes an enterprise idle power slot into the ledger."""
        with self._lock:
            offer_id = f"offer_{slot.slot_id}"
            offer = LeaseOffer(
                offer_id=offer_id,
                seller_id=slot.seller_id,
                seller_name=slot.seller_name,
                slot_id=slot.slot_id,
                compute_type=slot.compute_type.value,
                node_count=slot.node_count,
                start_hour=slot.start_hour,
                duration_hours=slot.duration_hours,
                price_per_node_hour_usd=slot.price_per_node_hour_usd,
                carbon_intensity_g_per_kwh=slot.carbon_intensity_g_per_kwh,
                total_power_kw=slot.total_power_kw,
            )
            self.offers[offer_id] = offer
            return offer

    def create_security_hold(self, slot: PowerSlot, job: WorkloadJob) -> ReservationContract:
        """
        Locks a provisional reservation in SECURITY_HOLD status.
        Prevents other buyers from claiming the capacity while security audits run.
        """
        with self._lock:
            contract_id = f"res_{slot.slot_id}_{job.job_id}"
            offer_id = f"offer_{slot.slot_id}"
            raw_rc = getattr(job, "risk_category", "benign")
            rc_str = raw_rc.value if hasattr(raw_rc, "value") else str(raw_rc)

            contract = ReservationContract(
                contract_id=contract_id,
                offer_id=offer_id,
                slot_id=slot.slot_id,
                job_id=job.job_id,
                seller_id=slot.seller_id,
                seller_name=slot.seller_name,
                buyer_id=job.buyer_id,
                buyer_name=job.buyer_name,
                compute_type=job.required_compute.value if hasattr(job.required_compute, "value") else str(job.required_compute),
                node_count=job.node_count,
                start_hour=slot.start_hour,
                duration_hours=job.estimated_duration_hours,
                agreed_price_per_node_hour=slot.price_per_node_hour_usd,
                total_power_kw=(slot.total_power_kw / slot.node_count) * job.node_count if slot.node_count > 0 else 0.0,
                status=ReservationStatus.SECURITY_HOLD,
                workload_description=job.workload_description,
                container_image=getattr(job, "container_image", ""),
                requested_capabilities=list(getattr(job, "requested_capabilities", [])),
                outbound_destinations=list(getattr(job, "outbound_destinations", [])),
                risk_category=rc_str,
                risk_tier=int(getattr(job, "risk_tier", 1)),
                risk_level_label=str(getattr(job, "risk_level_label", "Tier 1: Clearly Benign — Standard Isolated Compute")),
                threat_taxonomy=str(getattr(job, "threat_taxonomy", "None (Benign)")),
                ground_truth_safe=bool(getattr(job, "ground_truth_safe", True)),
            )

            # Emit receipt
            receipt = self._emit_receipt(
                contract=contract,
                action="HOLD_PLACED",
                carbon_saved_kg=self._calculate_carbon_savings(slot, job),
            )
            contract.receipt_ids.append(receipt.receipt_id)
            self.contracts[contract_id] = contract
            return contract

    def commit_reservation(
        self,
        contract_id: str,
        security_verdict: str,
        security_reason: str,
    ) -> ReservationContract:
        """
        Finalizes reservation upon successful Security Taskforce approval.
        """
        with self._lock:
            contract = self.contracts.get(contract_id)
            if not contract:
                raise ValueError(f"Contract {contract_id} not found.")

            contract.status = ReservationStatus.COMMITTED
            contract.security_verdict = security_verdict
            contract.security_reason = security_reason

            # Emit commit receipt
            receipt = self._emit_receipt(
                contract=contract,
                action="COMMITTED",
                carbon_saved_kg=0.0,
            )
            contract.receipt_ids.append(receipt.receipt_id)
            return contract

    def reject_reservation(
        self,
        contract_id: str,
        security_verdict: str,
        security_reason: str,
    ) -> ReservationContract:
        """
        Rejects provisional reservation when Security Taskforce vetoes migration.
        """
        with self._lock:
            contract = self.contracts.get(contract_id)
            if not contract:
                raise ValueError(f"Contract {contract_id} not found.")

            contract.status = ReservationStatus.REJECTED
            contract.security_verdict = security_verdict
            contract.security_reason = security_reason

            receipt = self._emit_receipt(
                contract=contract,
                action="SECURITY_REJECTED",
                carbon_saved_kg=0.0,
            )
            contract.receipt_ids.append(receipt.receipt_id)
            return contract

    def escalate_reservation(
        self,
        contract_id: str,
        security_reason: str,
    ) -> ReservationContract:
        """
        Escalates reservation to human security taskforce when models deadlock.
        """
        with self._lock:
            contract = self.contracts.get(contract_id)
            if not contract:
                raise ValueError(f"Contract {contract_id} not found.")

            contract.status = ReservationStatus.ESCALATED
            contract.security_verdict = "ESCALATED_TO_HUMAN"
            contract.security_reason = security_reason

            receipt = self._emit_receipt(
                contract=contract,
                action="ESCALATED",
                carbon_saved_kg=0.0,
            )
            contract.receipt_ids.append(receipt.receipt_id)
            return contract

    def settle_reservation(self, contract_id: str) -> LedgerReceipt:
        """
        Marks reservation as completed after workload execution and emits final billing receipt.
        """
        with self._lock:
            contract = self.contracts.get(contract_id)
            if not contract:
                raise ValueError(f"Contract {contract_id} not found.")

            contract.status = ReservationStatus.COMPLETED
            receipt = self._emit_receipt(
                contract=contract,
                action="SETTLED",
                carbon_saved_kg=round(contract.total_energy_kwh * 0.35, 2),  # Estimated baseline grid delta
            )
            contract.receipt_ids.append(receipt.receipt_id)
            return receipt

    def verify_audit_trail(self) -> bool:
        """
        Validates the integrity of the cryptographic receipt chain.
        Returns True if all SHA-256 hashes are valid and untampered.
        """
        with self._lock:
            prev_hash = self.GENESIS_HASH
            for r in self.receipts:
                if r.previous_receipt_hash != prev_hash:
                    return False
                if r.calculate_hash() != r.receipt_hash:
                    return False
                prev_hash = r.receipt_hash
            return True

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Calculates global marketplace metrics."""
        with self._lock:
            committed_contracts = [
                c for c in self.contracts.values()
                if c.status in (ReservationStatus.COMMITTED, ReservationStatus.COMPLETED)
            ]
            rejected_contracts = [c for c in self.contracts.values() if c.status == ReservationStatus.REJECTED]
            escalated_contracts = [c for c in self.contracts.values() if c.status == ReservationStatus.ESCALATED]

            total_hours = sum(c.node_count * c.duration_hours for c in committed_contracts)
            total_kwh = sum(c.total_energy_kwh for c in committed_contracts)
            total_usd = sum(c.total_cost_usd for c in committed_contracts)

            return {
                "total_offers": len(self.offers),
                "total_contracts": len(self.contracts),
                "committed_count": len(committed_contracts),
                "rejected_count": len(rejected_contracts),
                "escalated_count": len(escalated_contracts),
                "total_idle_harvested_node_hours": total_hours,
                "total_idle_harvested_kwh": round(total_kwh, 2),
                "total_marketplace_volume_usd": round(total_usd, 2),
                "receipt_chain_length": len(self.receipts),
                "chain_valid": self.verify_audit_trail(),
            }

    def _emit_receipt(self, contract: ReservationContract, action: str, carbon_saved_kg: float) -> LedgerReceipt:
        receipt_id = f"rcpt_{len(self.receipts) + 1:05d}_{int(time.time() * 1000) % 1000000}"
        receipt = LedgerReceipt(
            receipt_id=receipt_id,
            contract_id=contract.contract_id,
            action=action,
            seller_id=contract.seller_id,
            buyer_id=contract.buyer_id,
            node_count=contract.node_count,
            duration_hours=contract.duration_hours,
            total_energy_kwh=contract.total_energy_kwh,
            estimated_cost_usd=contract.total_cost_usd,
            carbon_saved_kg=carbon_saved_kg,
            timestamp=time.time(),
            previous_receipt_hash=self._last_receipt_hash,
        )
        receipt.receipt_hash = receipt.calculate_hash()
        self._last_receipt_hash = receipt.receipt_hash
        self.receipts.append(receipt)
        return receipt

    def _calculate_carbon_savings(self, slot: PowerSlot, job: WorkloadJob) -> float:
        # Savings = (Standard Daytime Grid Carbon - Off-peak Green Grid Carbon) * kWh
        # Benchmark daytime grid ~ 450 g/kWh; offpeak wind ~ 130 g/kWh -> delta ~ 320 g/kWh = 0.32 kg/kWh
        delta_kg_per_kwh = max(0.0, (450.0 - slot.carbon_intensity_g_per_kwh) / 1000.0)
        job_kwh = (slot.total_power_kw / slot.node_count) * job.node_count * job.estimated_duration_hours
        return round(job_kwh * delta_kg_per_kwh, 2)
