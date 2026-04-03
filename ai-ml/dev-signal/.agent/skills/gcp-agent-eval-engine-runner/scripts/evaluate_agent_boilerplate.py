import asyncio
import httpx
import json
import os
from vertexai import Client
from google.genai import types

async def fetch_agent_info(shadow_url: str, agent_name: str = "agent"):
    """Fetches instructions and tools from the ADK Agent Info API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{shadow_url}/apps/{agent_name}/agent-info")
        response.raise_for_status()
        return response.json()

async def _run_inference(semaphore, client, shadow_url, prompt, agent_name="agent"):
    """Hits the /run_sse endpoint and captures the reasoning trace."""
    async with semaphore:
        events = []
        final_answer = ""
        # The ADK path for execution
        url = f"{shadow_url}/apps/{agent_name}/run_sse"
        async with client.stream("POST", url, json={"prompt": prompt}) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event)
                    if event.get("type") == "answer":
                        final_answer = event.get("content", "")
        return {"response": final_answer, "intermediate_events": events}

async def run_evaluation_pipeline(shadow_url: str, dataset_path: str):
    """Full Cycle: Inference -> Vertex AI Eval -> Gating."""
    # 1. Fetch Agent Definition (for the Judge LLM)
    agent_info = await fetch_agent_info(shadow_url)
    
    # 2. Throttled Parallel Inference
    # ... (dataset loading logic) ...
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=300) as client:
        tasks = [_run_inference(sem, client, shadow_url, p) for p in prompts]
        results = await asyncio.gather(*tasks)

    # 3. Create Vertex AI Evaluation Run
    genai_client = Client(project=os.getenv("PROJECT_ID"), location="us-central1")
    eval_run = genai_client.evals.create_evaluation_run(
        dataset=enriched_dataset, # prompt + reference + actual_response + trace
        metrics=[
            types.RubricMetric.FINAL_RESPONSE_MATCH,
            types.RubricMetric.TOOL_USE_QUALITY,
            types.RubricMetric.HALLUCINATION
        ],
        agent_info=agent_info # Context for the judge
    )
    
    # 4. Gating Step (Success Criteria)
    THRESHOLD = 0.75
    if eval_run.state == types.EvaluationRunState.SUCCEEDED:
        for metric, values in eval_run.metrics.items():
            if values["mean"] < THRESHOLD:
                raise ValueError(f"Evaluation failed: {metric} mean {values['mean']} is below {THRESHOLD}")
    
    return eval_run
