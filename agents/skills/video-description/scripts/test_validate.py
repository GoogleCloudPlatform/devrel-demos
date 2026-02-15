import json
import os
import re

import pytest
from validate import validate_description

# Locate evaluations.json relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVALS_PATH = os.path.join(BASE_DIR, "../evaluations.json")

def load_evaluations():
    """Load evaluation cases from the JSON file."""
    if not os.path.exists(EVALS_PATH):
        return []
    with open(EVALS_PATH) as f:
        return json.load(f)

def mock_llm_generate(query) -> str:
    """Mocks an LLM response based on the query.
    In a real scenario, this would call an LLM API.
    """
    query_lower = query.lower()

    if "technical deep dive" in query_lower:
        return """# My Deep Dive into AI Agents

I am excited to share my latest findings on AI agents. I believe this will change how we work.

🚀 **Resources**: https://github.com/example/repo

## Key Takeaways
- Agents are autonomous
- JSON is the nervous system
- Testing matches industry standards

## Connect with me
- Twitter: @example
- LinkedIn: /in/example

#AI #Agents #Tech #Coding #DeepDive"""

    if "vacation video" in query_lower:
        return """# My Trip to Hawaii

I had an amazing time in Hawaii and I want to show you the highlights of my trip.

🚀 **Book your trip**: https://travel.com

## What's in this video?
- Surfing the big waves
- Hiking the volcano
- Eating poke bowls

## Timestamps
00:00 - Intro
01:30 - Beach
05:00 - Volcano
10:20 - Summary

#Travel #Hawaii #Vlog #Fun #Summer"""

    # Fallback for unknown queries
    return f"""# Generated Description for: {query}

I am generating a description based on your request.

🚀 **Link**: https://example.com

## Timestamps
00:00 - Start

#Tag1 #Tag2 #Tag3 #Tag4 #Tag5"""

def check_semantic_expectations(output, expected_behaviors):
    """Checks if the output meets semantic expectations using heuristics.
    Returns a list of failure messages.
    """
    failures = []
    output_lower = output.lower()

    for behavior in expected_behaviors:
        behavior_lower = behavior.lower()

        # 1. Check for "first-person"
        if "first-person" in behavior_lower or "i " in behavior_lower:
            if not re.search(r"\b(i|i'm|my)\b", output_lower):
                failures.append(f"Missing first-person perspective: '{behavior}'")

        # 2. Check for "hashtags"
        if "hashtag" in behavior_lower:
            count = len(re.findall(r"#\w+", output))
            # Extract number from behavior string (e.g., "exactly 5", "Includes 5", "5 broad appeal")
            match = re.search(r"(\d+)", behavior_lower)
            if match:
                expected_count = int(match.group(1))
                if ("exactly" in behavior_lower or "include" in behavior_lower or "broad appeal" in behavior_lower) and count != expected_count:
                     failures.append(f"Hashtag count mismatch (found {count}, expected {expected_count}): '{behavior}'")
                elif "fewer than" in behavior_lower and count >= expected_count:
                     failures.append(f"Hashtag count mismatch (found {count}, expected fewer than {expected_count}): '{behavior}'")
            else:
                # Fallback if no specific number is found but hashtag behavior is expected
                if count == 0:
                    failures.append(f"Missing hashtags: '{behavior}'")

    return failures

@pytest.mark.parametrize("test_case", load_evaluations())
def test_video_description_generation(test_case) -> None:
    """Test that the agent (mocked) generates a valid video description
    that meets both technical and semantic requirements.
    """
    query = test_case["query"]
    expected_behavior = test_case.get("expected_behavior", [])

    # 1. Generate Content
    output = mock_llm_generate(query)
    assert output, "Generated content should not be empty"

    # 2. Validate using the script (Technical Checks)
    errors, warnings = validate_description(output)

    # Allow warnings but fail on errors
    assert not errors, f"Validation script returned errors: {errors}"

    # Optional: We can assert on warnings if we want strict compliance,
    # but for now we just print them for visibility in failed tests.
    if warnings:
        print(f"Validation warnings: {warnings}")

    # 3. Check Semantic Expectations
    semantic_failures = check_semantic_expectations(output, expected_behavior)
    assert not semantic_failures, f"Semantic checks failed: {semantic_failures}"
