"""Domain tools for the Formula E track planner.

These are plain Python functions that ADK exposes to the model as tools. The
codelab provides this file; you write the agents that use it in `agent.py`.
"""

import json
import pathlib
from typing import Any

from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

_APP_DIR = pathlib.Path(__file__).resolve().parent
CIRCUITS_PATH = _APP_DIR / "data" / "circuits.json"
SKILL_DIR = _APP_DIR / "skills" / "fia-compliance-skill"

MIN_LENGTH_M = 2000
MAX_LENGTH_M = 3500
MIN_WIDTH_M = 10.0
MIN_REGEN_KW = 250.0
MANDATORY_CAD_LAYERS = (
    "F1_TRACK_CENTRELINE",
    "F1_PIT_ENTRY_SPEED_LIMIT_LANE",
    "F1_WALL_TEMP",
    "F1_TEC3",
)


def build_fia_skill_toolset() -> SkillToolset:
    """Loads the FIA compliance skill and wraps it in an ADK SkillToolset.

    The toolset gives the agent `list_skills`, `load_skill`,
    `load_skill_resource`, and `run_skill_script`, so it reads the skill only
    when it needs it.

    Returns:
        A SkillToolset that can run the skill's scripts locally.
    """
    return SkillToolset(
        skills=[load_skill_from_dir(SKILL_DIR)],
        code_executor=UnsafeLocalCodeExecutor(),
    )


def get_track_topology(venue: str) -> dict[str, Any]:
    """Returns the surveyed topology for a candidate Formula E venue.

    Args:
        venue: Venue name, for example 'London Docklands', 'Tokyo Bay',
            'Monaco Harbour', 'Sao Paulo', or 'Berlin Tempelhof'.

    Returns:
        The venue's length, minimum width, CAD layers, heavy braking zones, and
        notes, or an error listing the available venues.
    """
    venues = json.loads(CIRCUITS_PATH.read_text(encoding="utf-8"))["venues"]
    for name, topology in venues.items():
        if name.lower() in venue.lower() or venue.lower() in name.lower():
            return topology
    return {
        "error": f"Unknown venue '{venue}'.",
        "available_venues": sorted(venues),
    }


def evaluate_track_layout(
        circuit_name: str,
        total_length_m: int,
        minimum_width_m: float,
        peak_regen_kw: float,
        cad_layers: list[str],
) -> dict[str, Any]:
    """Checks a proposed layout against the FIA geometry, energy and CAD rules.

    Args:
        circuit_name: Name of the proposed circuit.
        total_length_m: Total circuit length in metres.
        minimum_width_m: Narrowest point of the track in metres.
        peak_regen_kw: Highest estimated braking regeneration in kW, taken from
            `calculate_regen_zones.py`.
        cad_layers: CAD layer names included in the blueprint.

    Returns:
        Whether the layout is compliant, a 0.0 to 1.0 score, and remediation
        notes for every failed check.
    """
    failures = []
    if not MIN_LENGTH_M <= total_length_m <= MAX_LENGTH_M:
        failures.append(
            f"Length {total_length_m}m is outside the "
            f"{MIN_LENGTH_M}m-{MAX_LENGTH_M}m range."
        )
    if minimum_width_m < MIN_WIDTH_M:
        failures.append(
            f"Minimum width {minimum_width_m}m is below the {MIN_WIDTH_M}m "
            "minimum."
        )
    if peak_regen_kw < MIN_REGEN_KW:
        failures.append(
            f"Peak regeneration {peak_regen_kw} kW is below the "
            f"{MIN_REGEN_KW} kW target."
        )
    missing_layers = [
        layer for layer in MANDATORY_CAD_LAYERS if layer not in cad_layers
    ]
    if missing_layers:
        failures.append(
            "Missing mandatory CAD layers: " + ", ".join(missing_layers) + "."
        )
    return {
        "circuit_name": circuit_name,
        "is_compliant": not failures,
        "score": round(1 - len(failures) / 4, 2),
        "missing_cad_layers": missing_layers,
        "remediation_notes": failures,
    }
