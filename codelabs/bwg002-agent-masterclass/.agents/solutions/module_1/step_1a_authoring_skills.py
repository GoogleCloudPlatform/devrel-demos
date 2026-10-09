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
 * @file step_1a_authoring_skills.py
 * @description Module 1 Step 1a reference solution: Authoring and loading on-demand
 *   ADK Agent Skills (`brand-guidelines/SKILL.md`) via `load_skill_from_dir` and
 *   `SkillToolset`.
 *
 * Why: Packaging house brand guidelines as an external `SKILL.md` with lightweight
 * YAML frontmatter enables progressive disclosure. The Visual Director agent sees
 * only the concise skill label up front and loads the full palette, lighting,
 * composition, subject, and forbidden-element rules on demand via `load_skill`.
 */
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
from typing import Any

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.agent import (  # noqa: E402
    Agent,
    App,
    Gemini,
    generate_key_visual,
    types,
)
from pitch_generator.app_utils.services import (  # noqa: E402
    ServiceContainer,
    get_default_services,
)
from pitch_generator.config import PitchConfig, get_config  # noqa: E402

DEFAULT_BRAND_SKILL_DIR: Path = Path(__file__).resolve().parent / "skills" / "brand-guidelines"

_FRONTMATTER_PATTERN = re.compile(
    r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)(.*)",
    flags=re.DOTALL,
)


@dataclass(frozen=True)
class Skill:
    """
    /**
     * Structured representation of an ADK Agent Skill parsed from a `SKILL.md` file.
     *
     * Why: Separates frontmatter discovery metadata (`name`, `description`) from the
     * full instructional `body` so `SkillToolset` can expose only the label in the
     * initial system prompt and load `body` on demand.
     *
     * @param name Unique lowercase-hyphen skill identifier (`"brand-guidelines"`).
     * @param description Third-person summary explaining what the skill does and when to load it.
     * @param body Full Markdown instructions body following the YAML frontmatter.
     * @param path Filesystem path to the source `SKILL.md` file.
     * @param frontmatter Parsed YAML frontmatter key-value mapping.
     */
    """

    name: str
    description: str
    body: str
    path: Path | None = None
    frontmatter: dict[str, str] = field(default_factory=dict)

    @property
    def instructions(self) -> str:
        """
        /**
         * Alias for `body` matching ADK skill instruction attribute conventions.
         *
         * Why: Allows callers inspecting either `.body` or `.instructions` to retrieve
         * the Markdown skill rules seamlessly.
         *
         * @return Full Markdown skill body.
         */
        """
        return self.body

    @property
    def content(self) -> str:
        """
        /**
         * Alias for `body` matching content extraction helpers.
         *
         * Why: Ensures opaque-box helpers probing `.content` receive the skill rules.
         *
         * @return Full Markdown skill body.
         */
        """
        return self.body

    def __str__(self) -> str:
        """
        /**
         * Return the skill body when coerced to `str`.
         *
         * Why: Enables callers that wrap `get_skill(...)` or `load_skill(...)` in `str()`
         * to inspect the house brand sections directly.
         *
         * @return Markdown body text.
         */
        """
        return self.body

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the skill definition into a plain dictionary.
         *
         * Why: Supports JSON serialization and `extract_field` inspection in tests.
         *
         * @return Dictionary with `name`, `description`, `body`, `instructions`, and `content`.
         */
        """
        return {
            "name": self.name,
            "description": self.description,
            "body": self.body,
            "instructions": self.body,
            "content": self.body,
            "path": str(self.path) if self.path else None,
        }


def load_skill_from_dir(skill_dir: str | Path | None = None) -> Skill:
    """
    /**
     * Parse and validate an ADK `SKILL.md` file from `skill_dir`.
     *
     * Why: Enforces ADK skill authoring invariants at load time: the directory and
     * `SKILL.md` must exist, YAML frontmatter must be properly opened and closed with
     * `---`, and both `name` and `description` must be non-empty.
     *
     * @param skill_dir Directory containing `SKILL.md` (defaults to `DEFAULT_BRAND_SKILL_DIR`).
     * @return Validated `Skill` instance.
     */
    """
    target_dir = Path(skill_dir) if skill_dir is not None else DEFAULT_BRAND_SKILL_DIR
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Skill directory does not exist: {target_dir}")

    skill_md_path = target_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise FileNotFoundError(f"Missing SKILL.md in skill directory: {target_dir}")

    raw_text = skill_md_path.read_text(encoding="utf-8")
    if not raw_text.startswith("---"):
        raise ValueError(f"SKILL.md in {target_dir} must start with YAML frontmatter '---'")

    match = _FRONTMATTER_PATTERN.match(raw_text)
    if match is None:
        raise ValueError(f"Unclosed or malformed YAML frontmatter in {skill_md_path}")

    frontmatter_raw, body_raw = match.group(1), match.group(2)
    parsed_fm: dict[str, str] = {}
    for line in frontmatter_raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"Invalid YAML frontmatter line in {skill_md_path}: {line!r}")
        key, val = stripped.split(":", 1)
        parsed_fm[key.strip()] = val.strip().strip('"').strip("'")

    name = parsed_fm.get("name", "").strip()
    description = parsed_fm.get("description", "").strip()
    if not name or not description:
        raise ValueError(
            f"SKILL.md in {target_dir} must define non-empty 'name' and 'description' in frontmatter"
        )

    body = body_raw.strip()
    if not body:
        raise ValueError(f"SKILL.md in {target_dir} has an empty instructions body")

    return Skill(
        name=name,
        description=description,
        body=body,
        path=skill_md_path,
        frontmatter=parsed_fm,
    )


def load_brand_skill(skill_dir: str | Path | None = None) -> Skill:
    """
    /**
     * Convenience helper that loads the house `brand-guidelines` skill.
     *
     * Why: Provides a zero-argument loader for callers that want the default
     * Module 1 `brand-guidelines` skill without constructing a path manually.
     *
     * @param skill_dir Optional custom skill directory override.
     * @return Loaded `brand-guidelines` `Skill` object.
     */
    """
    return load_skill_from_dir(skill_dir or DEFAULT_BRAND_SKILL_DIR)


class SkillToolset:
    """
    /**
     * ADK `SkillToolset` that registers skills and loads their bodies on demand.
     *
     * Why: Implements the Progressive Disclosure pattern by keeping full skill bodies
     * out of the initial context until the agent invokes `load_skill(skill_name)`,
     * while raising `KeyError` on unknown skill names to catch hallucinated tool calls.
     */
    """

    def __init__(self, skills: Sequence[Skill] | None = None) -> None:
        """
        /**
         * Initialize the toolset with a collection of `Skill` definitions.
         *
         * Why: Registers each `Skill` by name so `load_skill` can resolve it on demand.
         *
         * @param skills Sequence of `Skill` objects to register (defaults to `[BRAND_SKILL]`).
         */
        """
        skill_items = list(skills) if skills is not None else [load_brand_skill()]
        self._skills: dict[str, Skill] = {}
        for item in skill_items:
            if not isinstance(item, Skill):
                raise TypeError(f"Expected Skill instance, got {type(item).__name__}")
            self._skills[item.name] = item
        self.loaded_skills: list[str] = []

    @property
    def skills(self) -> list[Skill]:
        """
        /**
         * Return the list of registered `Skill` objects.
         *
         * Why: Allows inspection of which skills are attached to an `Agent`'s toolset.
         *
         * @return List of registered `Skill` instances.
         */
        """
        return list(self._skills.values())

    def list_skills(self) -> list[dict[str, str]]:
        """
        /**
         * Return lightweight frontmatter summaries for all registered skills.
         *
         * Why: Supplies the agent's initial context with skill names and descriptions
         * without injecting the full Markdown bodies.
         *
         * @return List of `{"name": ..., "description": ...}` dictionaries.
         */
        """
        return [
            {"name": skill.name, "description": skill.description}
            for skill in self._skills.values()
        ]

    def get_skill(self, skill_name: str) -> Skill:
        """
        /**
         * Retrieve a registered `Skill` object by name.
         *
         * Why: Validates that `skill_name` is registered in this toolset and raises
         * `KeyError` if an unregistered or empty skill name is requested.
         *
         * @param skill_name Name of the registered skill (e.g., `"brand-guidelines"`).
         * @return Matching `Skill` instance.
         */
        """
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError("skill_name must be a non-empty string")
        clean_name = skill_name.strip()
        if clean_name not in self._skills:
            raise KeyError(
                f"Skill {clean_name!r} is not registered in SkillToolset. "
                f"Available skills: {tuple(self._skills.keys())}"
            )
        return self._skills[clean_name]

    def load_skill(self, skill_name: str) -> str:
        """
        /**
         * Load the full Markdown instruction body for `skill_name` on demand.
         *
         * Why: Records that the agent explicitly loaded `skill_name` (used by Step 1b
         * Skill Evals) and returns the complete Markdown house rules.
         *
         * @param skill_name Name of the registered skill to load.
         * @return Full Markdown body of the skill.
         */
        """
        skill = self.get_skill(skill_name)
        if skill.name not in self.loaded_skills:
            self.loaded_skills.append(skill.name)
        return skill.body


BRAND_SKILL: Skill = load_skill_from_dir(DEFAULT_BRAND_SKILL_DIR)

MODEL: str = get_config().flash_model

visual_director = Agent(
    name="visual_director",
    model=Gemini(
        model=MODEL,
        client_kwargs={"location": get_config().location},
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Turns a campaign concept into art direction and a key visual.",
    instruction="""You are the Visual Director on a campaign pitch team.

Call `load_skill` for `brand-guidelines` before you write anything. The house
style is not optional and it is not in this prompt.

You are given a campaign concept. Then, in order:

1. Write art direction for ONE key visual that sells it, obeying the brand
guidelines: subject, composition, lighting, color, mood. Three or four
sentences.
2. Call `generate_key_visual` with exactly that art direction.

Your final reply is the art direction itself and nothing else. No preamble, no
alternatives, no questions back. Do not mention the skill, the tool, or the
image file — the image travels on its own.""",
    tools=[
        SkillToolset(skills=[BRAND_SKILL]),
        generate_key_visual,
    ],
    output_key="visual_director",
)

root_agent: Agent = visual_director

app = App(
    root_agent=root_agent,
    name="visual_director",
)


def generate_brand_aligned_art_direction(
    concept: str,
    *,
    services: ServiceContainer | None = None,
    toolset: SkillToolset | None = None,
    config: PitchConfig | None = None,
) -> str:
    """
    /**
     * Load the `brand-guidelines` skill via `SkillToolset` and generate compliant art direction.
     *
     * Why: Demonstrates the runtime progressive disclosure flow where the Visual Director
     * first loads `brand-guidelines` on demand and then synthesizes art direction governed
     * by the loaded Palette, Light, Composition, Subject, and Never sections.
     *
     * @param concept Campaign concept string to visualize.
     * @param services Optional injected `ServiceContainer`.
     * @param toolset Optional `SkillToolset` instance (defaults to a toolset with `BRAND_SKILL`).
     * @param config Optional `PitchConfig` override.
     * @return Brand-compliant art direction text.
     */
    """
    if not isinstance(concept, str) or not concept.strip():
        raise ValueError("concept must be a non-empty string")

    active_services = services or get_default_services(config)
    active_toolset = toolset or SkillToolset(skills=[BRAND_SKILL])
    skill_body = active_toolset.load_skill("brand-guidelines")

    combined_instruction = f"{visual_director.instruction}\n\n{skill_body}"
    return active_services.llm.generate_text(
        concept.strip(),
        system_instruction=combined_instruction,
        model=active_services.config.flash_model,
    )


__all__ = [
    "BRAND_SKILL",
    "DEFAULT_BRAND_SKILL_DIR",
    "MODEL",
    "Skill",
    "SkillToolset",
    "app",
    "generate_brand_aligned_art_direction",
    "load_brand_skill",
    "load_skill_from_dir",
    "root_agent",
    "visual_director",
]
