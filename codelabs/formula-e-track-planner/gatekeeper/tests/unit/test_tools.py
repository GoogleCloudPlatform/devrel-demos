"""Unit tests for the Gatekeeper's deterministic checklist tool."""

from app.tools import MANDATORY_CAD_LAYERS
from app.tools import verify_infrastructure_checklist


def test_checklist_approves_compliant_blueprint() -> None:
    """All layers, enough width and enough regen means approval."""
    result = verify_infrastructure_checklist(
        circuit_id="FIA-FE-2026-LON-01",
        cad_layers=list(MANDATORY_CAD_LAYERS),
        minimum_width_m=11.5,
        peak_regen_kw=507.7,
    )
    assert result["approved"]
    assert result["status"].startswith("APPROVED")
    assert not result["missing_cad_layers"]


def test_checklist_rejects_and_lists_missing_layers() -> None:
    """Missing layers or failed thresholds mean rejection."""
    result = verify_infrastructure_checklist(
        circuit_id="FIA-FE-2026-MCO-01",
        cad_layers=["F1_TRACK_CENTRELINE", "F1_WALL_TEMP"],
        minimum_width_m=6.8,
        peak_regen_kw=460.9,
    )
    assert not result["approved"]
    assert result["status"].startswith("REJECTED")
    assert result["missing_cad_layers"] == [
        "F1_PIT_ENTRY_SPEED_LIMIT_LANE",
        "F1_TEC3",
    ]
