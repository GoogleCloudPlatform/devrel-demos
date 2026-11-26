"""Deterministic checks used by the Digital Twin Gatekeeper agent."""

from typing import Any

MIN_WIDTH_M = 10.0
MIN_REGEN_KW = 250.0
MANDATORY_CAD_LAYERS = (
    "F1_TRACK_CENTRELINE",
    "F1_PIT_ENTRY_SPEED_LIMIT_LANE",
    "F1_WALL_TEMP",
    "F1_TEC3",
)


def verify_infrastructure_checklist(
        circuit_id: str,
        cad_layers: list[str],
        minimum_width_m: float,
        peak_regen_kw: float,
) -> dict[str, Any]:
    """Runs the final homologation checklist for a circuit blueprint.

    Args:
        circuit_id: FIA circuit identifier, for example 'FIA-FE-2026-LON-01'.
        cad_layers: CAD layer names included in the blueprint.
        minimum_width_m: Narrowest point of the track in metres.
        peak_regen_kw: Highest estimated braking regeneration in kW.

    Returns:
        Whether the circuit is approved, a status message, and any missing CAD
        layers.
    """
    missing_layers = [
        layer for layer in MANDATORY_CAD_LAYERS if layer not in cad_layers
    ]
    approved = (
        not missing_layers
        and minimum_width_m >= MIN_WIDTH_M
        and peak_regen_kw >= MIN_REGEN_KW
    )
    return {
        "circuit_id": circuit_id,
        "approved": approved,
        "status": (
            "APPROVED: cleared for Digital Twin simulation."
            if approved
            else "REJECTED: fix the missing layers or failed thresholds."
        ),
        "missing_cad_layers": missing_layers,
    }
