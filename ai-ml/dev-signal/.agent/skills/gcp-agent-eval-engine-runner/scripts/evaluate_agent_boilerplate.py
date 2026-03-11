import asyncio
import httpx
from vertexai import Client
from google.genai import types

async def _run_inference(semaphore, client, shadow_url, prompt):
    """Hits the /run_sse endpoint and captures the reasoning trace."""
    async with semaphore:
        events = []
        final_answer = ""
        async with client.stream("POST", f"{shadow_url}/run_sse", json={"prompt": prompt}) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event)
                    if event.get("type") == "answer":
                        final_answer = event.get("content", "")
        return {"response": final_answer, "intermediate_events": events}

async def run_parallel_eval(dataset_path: str, shadow_url: str):
    """Throttled parallel inference runner."""
    # 1. Load dataset
    # 2. Run Parallel Inference (Semaphore 10)
    sem = asyncio.Semaphore(10)
    tasks = [_run_inference(sem, httpx_client, shadow_url, p) for p in prompts]
    results = await asyncio.gather(*tasks)

    # 3. Create Vertex AI Evaluation Run
    client = Client(...)
    eval_run = client.evals.create_evaluation_run(
        dataset=enriched_dataset,
        metrics=[...],
        agent_info=fetch_agent_info(shadow_url) # LIVE schema integration
    )
    return eval_run
