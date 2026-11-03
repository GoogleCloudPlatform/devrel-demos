#!/usr/bin/env python3
"""Deterministic Gen3 Formula E regenerative braking calculator.

This is a simplified teaching model, not an official FIA or Formula E tool. It
estimates average regenerative braking power from the kinetic energy recovered
in a single braking zone and caps it at the Gen3 RESS limit of 600 kW
(350 kW rear + 250 kW front motor-generator units).

Example:
  calculate_regen_zones.py --entry-kph 215 --exit-kph 55 --brake-dist-m 82
"""

import argparse
import json
from typing import Any

GRAVITY_MPS2 = 9.81
GEN3_MIN_MASS_KG = 854.0  # Gen3 minimum weight including driver.
RECOVERY_EFFICIENCY = 0.78  # Simplified powertrain recovery efficiency.
GEN3_MAX_REGEN_KW = 600.0
REGEN_TARGET_KW = 250.0
TECPRO_DECELERATION_G = 2.0


def calculate_regen(
        entry_kph: float,
        exit_kph: float,
        brake_dist_m: float,
        mass_kg: float = GEN3_MIN_MASS_KG,
) -> dict[str, Any]:
    """Computes deceleration, regen power, and the required barrier layer.

    Args:
        entry_kph: Speed at the start of the braking zone in km/h.
        exit_kph: Speed at the apex of the corner in km/h.
        brake_dist_m: Length of the braking zone in metres.
        mass_kg: Car mass including driver in kilograms.

    Returns:
        A dictionary with the deceleration in G, the estimated regen power in
        kW (capped at 600 kW), whether the 250 kW target is met, and the
        barrier layer required for the deceleration.
    """
    v_in = entry_kph / 3.6
    v_out = exit_kph / 3.6
    delta_ke_joules = 0.5 * mass_kg * max(0.0, v_in**2 - v_out**2)
    avg_speed = max(1.0, (v_in + v_out) / 2.0)
    braking_time_s = max(0.1, brake_dist_m / avg_speed)
    decel_g = (v_in - v_out) / braking_time_s / GRAVITY_MPS2
    regen_kw = delta_ke_joules * RECOVERY_EFFICIENCY / braking_time_s / 1000.0
    capped_regen_kw = round(min(regen_kw, GEN3_MAX_REGEN_KW), 1)
    return {
        "entry_kph": entry_kph,
        "exit_kph": exit_kph,
        "brake_dist_m": brake_dist_m,
        "deceleration_g": round(decel_g, 2),
        "estimated_regen_kw": capped_regen_kw,
        "meets_250kw_target": capped_regen_kw >= REGEN_TARGET_KW,
        "required_barrier_layer": (
            "F1_TEC3" if decel_g >= TECPRO_DECELERATION_G else "F1_WALL_TEMP"
        ),
    }


def main() -> None:
    """Parses command-line arguments and prints the result as JSON."""
    parser = argparse.ArgumentParser(
        description="Estimate Formula E Gen3 regenerative braking power."
    )
    parser.add_argument("--entry-kph", type=float, required=True)
    parser.add_argument("--exit-kph", type=float, required=True)
    parser.add_argument("--brake-dist-m", type=float, required=True)
    parser.add_argument("--mass-kg", type=float, default=GEN3_MIN_MASS_KG)
    args = parser.parse_args()
    print(
        json.dumps(
            calculate_regen(
                entry_kph=args.entry_kph,
                exit_kph=args.exit_kph,
                brake_dist_m=args.brake_dist_m,
                mass_kg=args.mass_kg,
            )
        )
    )


if __name__ == "__main__":
    main()
