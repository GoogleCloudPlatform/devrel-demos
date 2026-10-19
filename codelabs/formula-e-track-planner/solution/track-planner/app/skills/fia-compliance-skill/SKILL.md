---
name: fia-compliance-skill
description: >
  FIA Formula E street circuit rules: length and width limits, mandatory CAD
  layers, barrier selection, and Gen3 regenerative braking estimates. Use when
  designing, checking or fixing a Formula E circuit layout.
---

# FIA Formula E Compliance

Follow these steps for every circuit you check.

1. **Read the rules.** Call `load_skill_resource` with
   `file_path="references/track_regulations.md"`.
2. **Estimate regeneration for every heavy braking zone.** Call
   `run_skill_script` with `file_path="scripts/calculate_regen_zones.py"` and
   `args={"entry-kph": <entry>, "exit-kph": <exit>, "brake-dist-m": <distance>}`.
   Never guess kW values. Use the highest `estimated_regen_kw` as the
   circuit's peak regeneration.
3. **Check barriers.** Any zone whose `required_barrier_layer` is `F1_TEC3`
   needs the `F1_TEC3` CAD layer.
4. **Report.** List every rule the layout fails and a concrete fix for each
   one.
