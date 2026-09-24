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

"""LLM-as-judge for `custom_brand_fit` (see eval_config.yaml).

Grades the Visual Director's art direction against the agent's own brand
guidelines. The rubric is not written here: it is read from
`visual_director/skills/brand-guidelines/SKILL.md` at grading time, so editing
the skill changes both what the agent is told and what the judge enforces. A
rubric copied into this file would drift from the skill the moment someone
tuned the palette.

This grades the art direction *text*, before any pixels exist. The rendered
image is scored separately in BigQuery with `ObjectRef` and `AI.SCORE`.
"""

import functools
import threading
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel

## The judge reads the same guidelines the agent loads through `load_skill`.
SKILL_RELATIVE_PATH = Path("visual_director") / "skills" / "brand-guidelines" / "SKILL.md"

JUDGE_MODEL = "gemini-3.8-flash"

_local = threading.local()


class _Verdict(BaseModel):
    score: int  # 1-5
    violations: list[str]
    explanation: str


def _client() -> genai.Client:
    """One client per grading thread.

    The eval SDK grades cases on its own thread pool; this initialization runs once
    per thread. Avoids creating a new client for each eval case, which would re-do
    ADC and the TLS handshake every time. Each thread gets its own client, because
    google-auth freezes the SSL context after the first connection when a client
    certificate is present.
    """
    client = getattr(_local, "client", None)
    if client is None:
        # AI Studio (GEMINI_API_KEY) or Agent Platform (ADC).
        client = _local.client = genai.Client()
    return client


def _skill_file() -> Path:
    """Locates SKILL.md whether the grader runs from the project root or elsewhere.

    This file normally sits at `<project>/tests/eval/brand_fit.py`, so the project
    root is two levels up. The working directory is checked too, because
    `agents-cli eval grade` can be pointed at a config from anywhere.
    """
    here = Path(__file__).resolve()
    roots = [*here.parents[2:4], Path.cwd(), *Path.cwd().parents[:2]]
    for root in roots:
        candidate = root / SKILL_RELATIVE_PATH
        if candidate.is_file():
            return candidate
    searched = "\n  ".join(str(root / SKILL_RELATIVE_PATH) for root in roots)
    raise FileNotFoundError(
        "brand_fit could not find the brand-guidelines skill. Run this from the "
        f"visual-director project root. Looked in:\n  {searched}"
    )


@functools.cache
def _guidelines() -> str:
    """The body of SKILL.md, without the YAML frontmatter.

    Cached: the skill does not change mid-run, and every eval case would
    otherwise re-read it off disk.
    """
    text = _skill_file().read_text(encoding="utf-8")
    ## Frontmatter is the label the agent sees before loading. The judge wants the
    ## rules themselves, which start after the closing `---`.
    if text.startswith("---"):
        _, _, body = text.partition("---")
        _, _, body = body.partition("---")
        if body.strip():
            return body.strip()
    return text.strip()


def evaluate(instance):
    prompt = (
        "You are the brand guardian for a campaign pitch team. Below are the house "
        "brand guidelines, followed by a campaign concept and the art direction an "
        "agent wrote for its key visual.\n\n"
        "Grade the art direction from 1 to 5 on how faithfully it follows the "
        "guidelines:\n"
        "  5 - every applicable rule is honored, and the palette, light, and "
        "composition are stated explicitly enough for an image model to render.\n"
        "  3 - broadly on-brand, but one or more rules are left vague or unstated.\n"
        "  1 - contradicts the guidelines, for example by calling for forbidden "
        "content, a second subject, or flat overhead light.\n\n"
        "Anything in the guidelines' 'Never' section is a hard failure: if the art "
        "direction asks for it, the score cannot exceed 2. A brief that requests "
        "forbidden treatment does not excuse the art direction from following the "
        "guidelines; the subject comes from the brief, the treatment from the "
        "guidelines.\n\n"
        "List each broken rule in `violations`, quoting the guideline. Return an "
        "empty list when nothing is broken.\n\n"
        f"===== BRAND GUIDELINES =====\n{_guidelines()}\n\n"
        f"===== CAMPAIGN CONCEPT =====\n{instance.get('prompt', '')}\n\n"
        f"===== ART DIRECTION =====\n{instance.get('response', '')}\n"
    )

    response = _client().models.generate_content(
        model=JUDGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,  # deterministic grading
            response_mime_type="application/json",
            response_schema=_Verdict,  # guaranteed schema-valid JSON
        ),
    )
    verdict = response.parsed
    if verdict is None:  # model returned nothing usable
        return {"score": 0, "explanation": response.text or ""}

    explanation = verdict.explanation
    if verdict.violations:
        explanation = f"{explanation}\nViolations: " + "; ".join(verdict.violations)
    return {"score": max(1, min(5, verdict.score)), "explanation": explanation}
