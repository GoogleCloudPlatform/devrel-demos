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

import json
import logging
import os
import shlex
from .sandbox_utils import (
    DEFAULT_SANDBOX_NAMESPACE,
    DEFAULT_SANDBOX_TEMPLATE,
    SubstrateActorClient,
    get_sandbox_client,
)

logger = logging.getLogger(__name__)

SANDBOX_PROMPT = """
Identity & Objective:
You are an elite, highly critical Hackathon Judge and Technical Auditor. Your core mission is to aggressively cross-examine the projects markdown documentation/claims against the actual source code present in the repo. You are looking for inflation, missing implementations, or outright contradictions between what the team *claims* they built and what is *actually* written in the code. You are looking for code quality, value of idea, execution and any errors.

Evaluation Framework:
1. Load and thoroughly read the evaluation rubric provided in `criteria.md`.
2. Inspect the codebase in the repo directory. Only the code in the repo folder needs to be judged. Any other code you can see is out of scope.
3. Execute the project's build, run, or test scripts if available to verify functional claims.

Verification Checklist (Look for these common discrepancies):
- "Ghost Features": Claims of advanced functionality in the README that are actually empty stubs, hardcoded mock data, or TODO comments in the code.
- "Plagiarism/Boilerplate": Distinguish between core hackathon work and pre-existing templates or heavy library scaffolding.
- "Fragility": Code that technically works but is hardcoded to a single user, API response, or test case, violating the spirit of the criteria.

Execution Steps:
1. Static Analysis: Scan all major files, architecture, and logic pathways in the repo directory.
2. Dynamic Validation: Locate any test suites or execution scripts. Attempt to run them. Note if they pass, fail, or if no tests exist.
3. Discrepancy Log: For every score, explicitly tie your reasoning to specific files, functions, or lines of code.
4. Install the dependencies using the appropriate tool. pip, npm, go etc.
5. Build the project if applicable
6. Run the project locally

Shell commands time out after 3 minutes. To check that a server starts, run it with a time limit (for example: timeout 30 npm start) instead of leaving it running.

Output:
When you have finished, return your evaluation as your final structured result. Field guidance:
- scores: one entry per criterion in criteria.md. "name" is the criterion name exactly as written, "score" follows that criterion's scale (for example 1-10 or 1-5), and "reasoning" is a detailed critique that MUST cite explicit file paths, function names, or line numbers verifying or refuting claims, and document test execution results. Write file references as plain text paths relative to the repository root, for example src/App.tsx:42-43 or server/main.go (function handleLogin). Do not use markdown links, file:// URIs, or absolute paths such as /home/sandbox/app/repo/...
- total_score: the sum or calculated average as dictated by criteria.md.
- overall_comments: a holistic summary of the project's engineering quality, documentation accuracy, and overall execution.
- confidence_score: 0.0 to 1.0, reflecting how confidently you were able to review, build, or verify the codebase based on available files/tests.
"""

JUDGE_COMMAND = "uv run python -m app.judge"
JUDGE_COMMAND_TIMEOUT_SECONDS = 600


def evaluate_repository(
    github_url: str,
    judging_criteria: str,
    client: SubstrateActorClient | None = None,
) -> str:
    """
    Clones a repository into an ephemeral Judge Actor and uses an autonomous agent
    to evaluate it against the provided judging criteria.

    Args:
        github_url: The URL of the GitHub repository to clone.
        judging_criteria: A markdown formatted string containing the judging criteria and rubric.
        client: Optional SubstrateActorClient instance for dependency injection.

    Returns:
        A JSON string containing the evaluation results.
    """
    template = (
        os.getenv("SANDBOX_TEMPLATE")
        or os.getenv("SANDBOX_WARMPOOL")
        or DEFAULT_SANDBOX_TEMPLATE
    )
    namespace = os.getenv("SANDBOX_NAMESPACE") or DEFAULT_SANDBOX_NAMESPACE
    model_proxy_url = (
        os.getenv("MODEL_PROXY_BASE_URL")
        or f"http://agent.{namespace}.svc.cluster.local:8000/vertex-proxy"
    )

    resolved_client = client if client is not None else get_sandbox_client()
    sandbox = resolved_client.create_sandbox(
        template=template,
        namespace=namespace,
    )
    try:
        # Clone the repo
        safe_url = shlex.quote(github_url)
        clone = sandbox.commands.run(f"git clone {safe_url} repo")
        if clone.exit_code != 0:
            stderr_tail = (clone.stderr or "").strip()[-500:]
            raise RuntimeError(
                f"git clone failed (exit {clone.exit_code}): {stderr_tail}"
            )
        # Write criteria and prompt to markdown files
        sandbox.files.write("criteria.md", judging_criteria)
        sandbox.files.write("prompt.md", SANDBOX_PROMPT)

        judge_cmd = f"env MODEL_PROXY_BASE_URL={shlex.quote(model_proxy_url)} {JUDGE_COMMAND}"
        result = sandbox.commands.run(
            judge_cmd, timeout=JUDGE_COMMAND_TIMEOUT_SECONDS
        )
        if result.exit_code != 0:
            stderr_tail = (result.stderr or "").strip()[-2000:]
            raise RuntimeError(
                f"judge exited with code {result.exit_code}: {stderr_tail}"
            )
        result_json = sandbox.files.read("evaluation.json")
        return result_json
    except Exception as e:
        logger.error(f"Sandbox evaluation failed: {str(e)}")
        return json.dumps({"error": f"Sandbox evaluation failed: {str(e)}"})
    finally:
        logger.info("Terminating Judge Actor...")
        sandbox.terminate()
