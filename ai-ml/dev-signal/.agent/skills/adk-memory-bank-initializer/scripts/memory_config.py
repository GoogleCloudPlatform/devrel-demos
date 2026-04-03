import os
import vertexai
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService

def setup_memory_service(project_id: str, location: str, agent_engine_name: str):
    """
    Initializes the Vertex AI Memory Bank service.
    Note: The memory bank must be provisioned in a regional location (e.g., us-central1).
    """
    vertexai.init(project=project_id, location=location)
    
    # In production, the URI typically points to the Agent Engine resource
    # agentengine://projects/{project}/locations/{location}/agentEngines/{id}
    return VertexAiMemoryBankService(
        project=project_id,
        location=location,
        agent_engine_id=agent_engine_name # Or actual resource ID
    )

async def save_session_to_memory_callback(*args, **kwargs) -> None:
    """
    Defensive callback to persist session history to the Vertex AI memory bank.
    Register this in after_agent_callback.
    """
    ctx = kwargs.get("callback_context") or (args[0] if args else None)
    
    if ctx and hasattr(ctx, "_invocation_context") and ctx._invocation_context.memory_service:
        await ctx._invocation_context.memory_service.add_session_to_memory(
            ctx._invocation_context.session
        )
