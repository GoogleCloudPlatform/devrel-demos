# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
/**
 * @file test_module_1.py
 * @description Unit and integration tests for Module 1 reference solutions (Steps 1a–1c).
 *
 * Why: Verifies that every Module 1 learning progression step—authoring on-demand
 * ADK skills (`1a`), skill evaluation harnesses (`1b`), and Remote A2A Visual Director (`1c`)—
 * executes deterministically and 100% offline.
 */
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
from typing import Any
import pytest

APP_ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS_M1 = APP_ROOT / ".agents" / "solutions" / "module_1"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def _load_step(filename: str) -> Any:
    """
    /**
     * Dynamically loads a Module 1 solution module from `.agents/solutions/module_1/`.
     *
     * Why: Isolates each step's module namespace while testing `.agents/solutions/module_1/` files.
     *
     * @param filename Filename inside `.agents/solutions/module_1/`.
     * @return Loaded Python module object.
     */
    """
    target = SOLUTIONS_M1 / filename
    assert target.is_file(), f"Missing solution file: {target}"
    module_name = f"_test_m1_{target.stem}"
    spec = importlib.util.spec_from_file_location(module_name, target)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# Step 1a — Authoring Agent Skills & SkillToolset (F8)
# ===========================================================================


def test_step_1a_authoring_skills_and_skill_toolset() -> None:
    """
    /**
     * Verifies `brand-guidelines/SKILL.md` frontmatter, `load_skill_from_dir`, and `SkillToolset` on-demand loading.
     *
     * Why: Confirms Step 1a (`F8`) packages house brand rules with valid YAML frontmatter and loads the Markdown body progressively via `SkillToolset`.
     *
     * @return None.
     */
    """
    mod = _load_step("step_1a_authoring_skills.py")
    skill_md = SOLUTIONS_M1 / "skills" / "brand-guidelines" / "SKILL.md"
    assert skill_md.is_file()

    skill = mod.load_skill_from_dir(skill_md.parent)
    assert skill.name == "brand-guidelines"
    assert "use when" in skill.description.lower()

    toolset = mod.SkillToolset(skills=[skill])
    body = toolset.load_skill("brand-guidelines")
    for section in ("## palette", "## light", "## composition", "## subject", "## never"):
        assert section in body.lower()
    assert "brand-guidelines" in toolset.loaded_skills

    art = mod.generate_brand_aligned_art_direction("A commuter bike built for rainy cities")
    assert "indigo" in art.lower()
    assert "raking" in art.lower()

    with pytest.raises(KeyError):
        toolset.load_skill("nonexistent-skill")


# ===========================================================================
# Step 1b — Skill Evals (F9)
# ===========================================================================


def test_step_1b_skill_evals_rubric_and_suite() -> None:
    """
    /**
     * Verifies `evaluate_brand_skill` and `run_eval_suite` score compliant vs drifted art direction accurately.
     *
     * Why: Confirms Step 1b (`F9`) enforces both skill loading (`"brand-guidelines" in loaded_skills`) and the 5 house brand sections.
     *
     * @return None.
     */
    """
    mod = _load_step("step_1b_skill_evals.py")
    good_art = (
        "One realistic photographic subject placed off-center one-third into the frame "
        "with generous negative space opposite, shallow depth of field, deep indigo and slate "
        "ground with warm amber accent, low raking golden hour light with long shadows."
    )
    res_good = mod.evaluate_brand_skill(good_art, loaded_skills=["brand-guidelines"])
    assert res_good.passed is True
    assert res_good.loaded_skill is True
    assert res_good.score >= 0.8
    assert res_good.violations == []

    res_unloaded = mod.evaluate_brand_skill(good_art, loaded_skills=[])
    assert res_unloaded.passed is False
    assert res_unloaded.loaded_skill is False

    bad_art = "Neon cyan and magenta 3D render with company logo watermark and flat overhead ring light."
    res_bad = mod.evaluate_brand_skill(bad_art, loaded_skills=["brand-guidelines"])
    assert res_bad.passed is False
    assert len(res_bad.violations) >= 2

    suite_summary = mod.run_eval_suite()
    assert suite_summary["total"] >= 4
    assert suite_summary["all_expectations_met"] is True


# ===========================================================================
# Step 1c — Remote A2A Visual Director Service & Client (F11)
# ===========================================================================


def test_step_1c_agent_card_and_generate_key_visual() -> None:
    """
    /**
     * Verifies `AgentCardBuilder`, well-known path, and `generate_key_visual` artifact saving.
     *
     * Why: Confirms Step 1c (`F11`) publishes a valid A2A Agent Card and persists generated key visuals into the tool context.
     *
     * @return None.
     */
    """
    mod = _load_step("step_1c_remote_a2a_visual_director.py")
    assert mod.AGENT_CARD_WELL_KNOWN_PATH == "/.well-known/agent-card.json"

    builder = mod.AgentCardBuilder(
        agent=mod.visual_director,
        rpc_url="http://localhost:8801/a2a/visual_director",
    )
    card = builder.build()
    assert card["name"] == "visual_director"
    assert card["url"] == "http://localhost:8801/a2a/visual_director"
    assert card["preferredTransport"] == "JSONRPC"

    ctx = mod.ToolContext()
    res = asyncio.run(
        mod.generate_key_visual(
            "Dramatic studio lighting on obsidian water bottle",
            ctx,
        )
    )
    assert res["filename"] == "key_visual.png"
    assert res["version"] == 1
    assert res["bytes"] > 0
    assert res["mime_type"] == "image/png"
    assert "key_visual.png" in ctx.artifacts

    with pytest.raises(ValueError, match="returned no image"):
        asyncio.run(
            mod.generate_key_visual("Art direction", ctx, simulate_no_image=True)
        )


def test_step_1c_cloud_run_client_part_converter_and_package() -> None:
    """
    /**
     * Verifies `_cloud_run_client`, `_pitch_parts_only`, and `package` key visual validation.
     *
     * Why: Confirms Step 1c (`F11`) signs `https://` Cloud Run requests, filters tool-call parts, and enforces image presence in `package`.
     *
     * @return None.
     */
    """
    mod = _load_step("step_1c_remote_a2a_visual_director.py")
    assert mod._cloud_run_client("http://localhost:8801") is None
    assert mod._cloud_run_client("http://127.0.0.1:8801") is None
    assert mod._cloud_run_client("") is None
    https_client = mod._cloud_run_client("https://visual-director-run.a.run.app")
    assert https_client is not None
    assert https_client.timeout == 600.0

    fc_part = mod.Part(function_call={"name": "generate_key_visual", "args": {}})
    fr_part = mod.Part(function_response={"name": "generate_key_visual", "response": {}})
    txt_part = mod.Part(text="Moody amber rim lighting")
    img_part = mod.Part(inline_data=mod.Blob(data=b"\x89PNG\r\n\x1a\n", mime_type="image/png"))

    assert mod._pitch_parts_only(fc_part) is None
    assert mod._pitch_parts_only(fr_part) is None
    assert mod._pitch_parts_only(txt_part) is not None
    assert mod._pitch_parts_only(img_part) is not None

    empty_ctx = mod.Context()
    node_input = {
        "creative_director": "Storm-ready shell",
        "copywriter": "Dry on arrival.",
        "visual_director": "Indigo slate studio lighting",
    }
    with pytest.raises(ValueError, match="no image"):
        list(mod.package(empty_ctx, node_input))

    valid_ctx = mod.create_mock_context_with_visual()
    events = list(mod.package(valid_ctx, node_input))
    combined = "\n".join(str(getattr(e, "output", "") or "") for e in events)
    for section in ("CONCEPT", "COPY", "ART DIRECTION", "KEY VISUAL"):
        assert section in combined
