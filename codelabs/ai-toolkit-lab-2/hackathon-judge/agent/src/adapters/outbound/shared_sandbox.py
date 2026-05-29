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

import os
import json
import logging
import shlex
from .sandbox_utils import get_sandbox_client

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

Output Specification:
Write your final evaluation strictly as a valid JSON object directly to `evaluation.json`. Do not include any markdown formatting wrappers (like ```json) inside the file itself. 

The JSON must strictly adhere to this schema:
{
"scores": [
{
    "name": "String (The specific criteria name from criteria.md)",
    "score": "Number (Based on the criteria scale, e.g., 1-10 or 1-5)",
    "reasoning": "String (Detailed critique. MUST include explicit file paths, function names, or line numbers verifying or refuting claims. Document test execution results here.)"
}
],
"total_score": "Number (The sum or calculated average as dictated by criteria.md)",
"overall_comments": "String (A holistic summary of the project's engineering quality, documentation accuracy, and overall execution.)",
"confidence_score": "Number (Scale of 0.0 to 1.0, reflecting how confidently you were able to review, build, or verify the codebase based on available files/tests.)"
}
"""

def evaluate_repository(github_url: str, judging_criteria: str) -> str:
    """
    Clones a repository into a secure sandbox and uses an autonomous agent to evaluate it 
    against the provided judging criteria.
    
    Args:
        github_url: The URL of the GitHub repository to clone.
        judging_criteria: A markdown formatted string containing the judging criteria and rubric.
        
    Returns:
        A JSON string containing the evaluation results.
    """
    template = os.getenv("SANDBOX_TEMPLATE")
    if not template:
        raise ValueError("SANDBOX_TEMPLATE environment variable is required")
    namespace = os.getenv("SANDBOX_NAMESPACE")
    if not namespace:
        raise ValueError("SANDBOX_NAMESPACE environment variable is required")
    
    client = get_sandbox_client()
    sandbox = client.create_sandbox(
        template=template,
        namespace=namespace,
    )
    try:
        # Clone the repo
        safe_url = shlex.quote(github_url)
        sandbox.commands.run(f"git clone {safe_url} repo")
        # Write criteria to markdown file
        sandbox.files.write('criteria.md', judging_criteria)
        
        sandbox.files.write('prompt.md', SANDBOX_PROMPT)
        prompt = 'gemini --yolo -p "Use @criteria.md as a guide and follow @prompt.md for the prompt. Make sure the output is in JSON format and written to evaluation.json"'
        sandbox.commands.run(prompt, timeout=600)
        result_json = sandbox.files.read('evaluation.json')
        return result_json
    except Exception as e:
        logger.error(f"Sandbox evaluation failed: {str(e)}")
        return json.dumps({"error": f"Sandbox evaluation failed: {str(e)}"})
    finally:
        logger.info("Terminating sandbox...")
        sandbox.terminate()
