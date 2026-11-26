"""Unit tests for the track planner's deterministic tools and skill script.

These tests make no Gemini calls, so they are fast and free to run.
"""

import importlib.util
import pathlib
import types

from app.tools import evaluate_track_layout
from app.tools import get_track_topology
from app.tools import MANDATORY_CAD_LAYERS

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "app"
    / "skills"
    / "fia-compliance-skill"
    / "scripts"
    / "calculate_regen_zones.py"
)


def _load_regen_script() -> types.ModuleType:
    """Imports the skill script as a module so its function can be tested."""
    spec = importlib.util.spec_from_file_location("regen", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_get_track_topology_known_and_unknown_venues() -> None:
    """Known venues return their topology; unknown ones list alternatives."""
    london = get_track_topology("London Docklands")
    assert london["circuit_id"] == "FIA-FE-2026-LON-01"
    assert london["total_length_m"] == 2400

    assert get_track_topology("monaco")["minimum_width_m"] == 6.8

    unknown = get_track_topology("Silverstone")
    assert "error" in unknown
    assert "Tokyo Bay" in unknown["available_venues"]


def test_evaluate_track_layout_passes_compliant_layout() -> None:
    """A layout that meets every rule is compliant with a full score."""
    result = evaluate_track_layout(
        circuit_name="ExCeL London",
        total_length_m=2400,
        minimum_width_m=11.5,
        peak_regen_kw=507.7,
        cad_layers=list(MANDATORY_CAD_LAYERS),
    )
    assert result["is_compliant"]
    assert result["score"] == 1.0
    assert not result["remediation_notes"]


def test_evaluate_track_layout_reports_every_failure() -> None:
    """A layout that breaks all four rules scores zero and lists each fix."""
    result = evaluate_track_layout(
        circuit_name="Bad Draft",
        total_length_m=4350,
        minimum_width_m=6.8,
        peak_regen_kw=102.3,
        cad_layers=["F1_TRACK_CENTRELINE", "F1_WALL_TEMP"],
    )
    assert not result["is_compliant"]
    assert result["score"] == 0.0
    assert result["missing_cad_layers"] == [
        "F1_PIT_ENTRY_SPEED_LIMIT_LANE",
        "F1_TEC3",
    ]
    assert len(result["remediation_notes"]) == 4


def test_regen_script_matches_codelab_examples() -> None:
    """The skill script returns the values quoted in the codelab."""
    regen = _load_regen_script()

    turn_10 = regen.calculate_regen(entry_kph=215, exit_kph=55, brake_dist_m=82)
    assert turn_10["deceleration_g"] == 2.07
    assert turn_10["estimated_regen_kw"] == 507.7
    assert turn_10["meets_250kw_target"]
    assert turn_10["required_barrier_layer"] == "F1_TEC3"

    slow_corner = regen.calculate_regen(
        entry_kph=140, exit_kph=65, brake_dist_m=110
    )
    assert slow_corner["estimated_regen_kw"] == 102.3
    assert not slow_corner["meets_250kw_target"]
    assert slow_corner["required_barrier_layer"] == "F1_WALL_TEMP"


def test_regen_script_caps_at_gen3_limit() -> None:
    """Extreme braking is capped at the 600 kW Gen3 limit."""
    regen = _load_regen_script()
    extreme = regen.calculate_regen(entry_kph=300, exit_kph=40, brake_dist_m=55)
    assert extreme["estimated_regen_kw"] == 600.0
