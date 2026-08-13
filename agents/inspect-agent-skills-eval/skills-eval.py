# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json, math, os
from pathlib import Path
from typing import Any, Dict, List

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Scorer, accuracy, model_graded_qa, multi_scorer, stderr, value_to_float
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sample_limits
from inspect_swe import gemini_cli

# Guard check for API key configuration
if "GEMINI_API_KEY" not in os.environ:
    raise ValueError("Missing GEMINI_API_KEY. Please set GEMINI_API_KEY environment variable.")


# --- Constants ---
# Fixed grader model; kept distinct from tested models to isolate solver performance and quota.
# Using a lightweight model for objective fact-verification maximizes evaluation throughput,
# reduces API cost, and provides consistent grading across evaluation runs.
GRADER_MODEL = "google/gemini-3.1-flash-lite"
QUESTIONS_FILE = "questions.json"
SYSTEM_PROMPT_FILE = "thrifty_system_prompt.txt"
SKILLS_FOLDER = "google-skills"

# Web search defaults to false (`-T web_access=false`).
# Pass `-T web_access=true` to enable web search (uses additional tokens and search API quota; reflects how these evaluations are run during development).
WEB_ACCESS_ALLOWED_INSTRUCTION = "- You may use external web search tools (e.g., `google_web_search`) if needed."
WEB_ACCESS_PROHIBITED_INSTRUCTION = "- Do NOT attempt to use external web search tools (e.g., `google_web_search`)."


# Symmetrical Skill paths inside your google-skills directory
SKILLS_PATHS: Dict[str, str] = {
    "gemini-api": "skills/cloud/gemini-api",
    "gcloud": "skills/cloud/gcloud",
}

def get_path_in_script_dir(file_path: str) -> Path: return Path(__file__).parent / file_path

def load_config(file_path: str = QUESTIONS_FILE) -> Dict[str, Any]:
    """Loads configuration from the questions file."""
    with open(get_path_in_script_dir(file_path), "r", encoding="utf-8") as f:
        return json.load(f)["config"]

def load_questions(file_path: str = QUESTIONS_FILE) -> Dict[str, List[Dict[str, Any]]]:
    """Loads questions from a JSON file and groups them by skill."""
    with open(get_path_in_script_dir(file_path), "r", encoding="utf-8") as f:
        questions_list = json.load(f)["questions"]
        
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in questions_list:
        grouped.setdefault(item["skill"], []).append(item)
    return grouped

def load_system_prompt(file_path=SYSTEM_PROMPT_FILE, web_access=False):
    """Loads the system prompt from a template file and interpolates runtime task parameters.
    
    Format placeholders in `thrifty_system_prompt.txt`:
    - `{time_limit_str}`: Derived from Inspect CLI `--time-limit N` (e.g. "300 seconds") or defaults to "an automated budget".
    - `{web_access_instruction}`: Conditionally resolved from Inspect CLI `-T web_access=false|true` to inject
      either `WEB_ACCESS_PROHIBITED_INSTRUCTION` or `WEB_ACCESS_ALLOWED_INSTRUCTION`.
    """
    runtime_sample_time_limit = sample_limits().time.limit
    formatted_prompt_time_limit = f"{runtime_sample_time_limit} seconds" if runtime_sample_time_limit else "an automated budget"
    web_access_instruction = (
        WEB_ACCESS_ALLOWED_INSTRUCTION
        if web_access
        else WEB_ACCESS_PROHIBITED_INSTRUCTION
    )
    with open(get_path_in_script_dir(file_path), "r", encoding="utf-8") as f:
        return f.read().format(time_limit_str=formatted_prompt_time_limit, web_access_instruction=web_access_instruction)

# --- Dynamic Configuration Derivation ---
_config = load_config()
SCORING_SCALE = _config["scoring_scale"]
MAX_FACTS = _config["max_facts"]


# Note: While model_graded_qa supports partial credit (partial_credit=True emitting 'P' -> 0.5),
# atomic fact verification is kept strictly binary ('C'|'I') to eliminate grader ambiguity.
def make_fact_scorer(index: int) -> Scorer:
    """Creates a scorer that checks a specific fact index."""
    template = f"""
    Does the submission satisfy this criteria: {{fact_{index}}}?
    
    [Submission]: {{answer}}
    
    {{instructions}}
    """
    inner_scorer = model_graded_qa(template=template, model=GRADER_MODEL)
    
    # Async is required by the Inspect AI Scorer protocol to support concurrent LLM grading calls.
    async def score(state: Any, target: Any) -> Any:
        fact = state.metadata.get(f"fact_{index}")
        if not fact:
            return None
        score_result = await inner_scorer(state, target)
        if score_result:
            if score_result.metadata is None:
                score_result.metadata = {}
            score_result.metadata["fact_index"] = index
        return score_result
    
    return score

fact_scorers = [make_fact_scorer(index) for index in range(MAX_FACTS)]

def custom_reducer(scores: List[Score]) -> Score:
    """Converts a list of categorical scores ('C'|'I') into a curved sample score."""
    numeric_scores = []
    breakdown = {}
    
    to_float = value_to_float()
    # Map categorical score ('C'|'I') to float (1.0|0.0)
    for score in scores:
        index = score.metadata["fact_index"]
        val = score.value
            
        breakdown[f"fact_{index}"] = val
        numeric_scores.append(to_float(val))
        
    # Calculate mean fact accuracy
    mean_score = sum(numeric_scores) / len(numeric_scores)
    # Quadratic curving (square mean -> scale & floor -> normalize)
    curved_score = math.floor(SCORING_SCALE * (mean_score ** 2)) / SCORING_SCALE
    
    return Score(
        value=curved_score,
        metadata={"breakdown": breakdown, "mean_score": mean_score}
    )

# === EVALUATION HELPERS ===

def get_questions_for_skill(skill_name: str, use_skill: bool) -> List[Sample]:
    """Generates evaluation questions with precise metadata for Looker cohort analysis."""
    skills_questions = load_questions()
    questions = skills_questions.get(skill_name, [])
    cohort_name = f"{skill_name} ({'Skill' if use_skill else 'Baseline'})"
    
    samples = []
    for question in questions:
        facts = question.get("facts", [])
        metadata = {"skill_group": cohort_name}
        for index, fact in enumerate(facts):
            if index < MAX_FACTS:
                metadata[f"fact_{index}"] = fact
        
        samples.append(
            Sample(
                input=question["prompt"],
                target="", # Target is handled by facts in metadata
                metadata=metadata
            )
        )
    return samples

@solver
def dynamic_gemini_cli(skills=None, web_access=False, version="0.51.0") -> Solver:
    """Solver wrapper that evaluates load_system_prompt() during sample execution."""
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        system_prompt = load_system_prompt(web_access=web_access)
        cli_solver = gemini_cli(skills=skills, system_prompt=system_prompt, version=version)
        return await cli_solver(state)
    return solve

def run_eval_task(skill_name: str, use_skill: bool, agent_skills_folder: str = SKILLS_FOLDER, time_limit=None, web_access=False) -> Task:
    """Core evaluation engine helper invoked by static @tasks."""
    cli_task_time_limit = time_limit
    task_config_time_limit = int(cli_task_time_limit) if cli_task_time_limit is not None and str(cli_task_time_limit).isdigit() else None
    questions = get_questions_for_skill(skill_name, use_skill)
    
    if use_skill:
        skills_path = Path.cwd() / agent_skills_folder / SKILLS_PATHS[skill_name]
        skills = [str(skills_path)]
    else:
        skills = []
        
    return Task(
        dataset=questions,
        # Pin gemini-cli version for cross environment reproducibility and to avoid pull quota limitations
        solver=dynamic_gemini_cli(skills=skills, web_access=web_access, version="0.51.0"),
        scorer=multi_scorer(scorers=fact_scorers, reducer=custom_reducer),
        metrics=[accuracy(), stderr()],
        time_limit=task_config_time_limit,
        sandbox="docker",
    )

# === STATIC TASK DEFINITIONS ===
# Each @task uses **kwargs delegation to forward CLI task arguments (e.g., `-T web_access=false`, `-T time_limit=300`)
# directly to `run_eval_task`, eliminating signature boilerplate across static task wrappers while remaining fully dynamic.

@task
def gemini_api_baseline(**kwargs):
    return run_eval_task("gemini-api", False, **kwargs)

@task
def gemini_api_skill(**kwargs):
    return run_eval_task("gemini-api", True, **kwargs)

@task
def gcloud_baseline(**kwargs):
    return run_eval_task("gcloud", False, **kwargs)

@task
def gcloud_skill(**kwargs):
    return run_eval_task("gcloud", True, **kwargs)
