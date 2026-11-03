# FIA Appendix O: Formula E Street Circuit Rules (Teaching Summary)

This is a simplified summary written for the codelab. It is not the official
FIA regulation text.

## 1. Geometry

| Rule | Limit |
| :--- | :--- |
| Total circuit length | 2000m to 3500m |
| Minimum track width | 10.0m at every point |

## 2. Barriers and Run-off

| Braking deceleration | Required barrier layer |
| :--- | :--- |
| Less than 2.0G | `F1_WALL_TEMP` (temporary concrete blocks) |
| 2.0G or more | `F1_TEC3` (Tecpro energy-absorbing barrier) |

## 3. Mandatory CAD Layers

Every homologation submission must include these four layers:

- `F1_TRACK_CENTRELINE`: surveyed racing line and sector splits.
- `F1_PIT_ENTRY_SPEED_LIMIT_LANE`: pit entry and 50 kph speed-limit lane.
- `F1_WALL_TEMP`: temporary concrete barrier blocks.
- `F1_TEC3`: Tecpro barriers at high-deceleration corners.

When a layout affects hospital or emergency access, it must also include:

- `F1_MEDICAL_CENTRE_TEXT`: medical centre and extrication route.
- `F1_HELIPAD`: emergency evacuation landing zone.

## 4. Gen3 Energy

- The Gen3 car recovers up to 600 kW under braking (350 kW rear + 250 kW
  front).
- At least one braking zone must reach 250 kW or more of estimated
  regeneration. Use `scripts/calculate_regen_zones.py` to estimate it; never
  guess.

## 5. Attack Mode

- The activation zone must be off the racing line.
- It must cost 1.0s to 1.5s compared with the racing line.
