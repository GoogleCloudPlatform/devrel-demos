# Step solutions

Each file here is the **final state of the file a learner edits in a given step**
of the lab. They exist so anyone who gets stuck (or falls behind) can copy the
finished file over their own and carry on.

| Step in the lab | File you edit | Solution file |
| --- | --- | --- |
| Orchestrate agents with a graph workflow | `pitch-generator/pitch_generator/agent.py` | `step-1-pitch_generator-agent.py` |
| Give an agent a skill (brand guidelines) | `visual-director/visual_director/skills/brand-guidelines/SKILL.md` | `step-2-brand-guidelines-SKILL.md` |
| Give an agent a skill (agent wiring) | `visual-director/visual_director/agent.py` | `step-2-visual_director-agent.py` |
| Equip an agent with an image generation tool | `visual-director/visual_director/agent.py` | `step-3-visual_director-agent.py` |
| Multi-agent architecture with A2A | `visual-director/visual_director/app_utils/a2a.py` | `step-4-visual_director-a2a.py` |
| Embed the A2A remote agent in the workflow | `pitch-generator/pitch_generator/agent.py` | `step-5-pitch_generator-agent.py` |

To use one, copy it over the file you are editing, for example:

```bash
cp ~/devrel-demos/codelabs/bwg-multi-agent-pitch-generator/steps/step-1-pitch_generator-agent.py \
  ~/devrel-demos/codelabs/bwg-multi-agent-pitch-generator/pitch-generator/pitch_generator/agent.py
```

The complete, deployable projects live in `../solution/`.
