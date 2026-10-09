// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Clean, zero-crossing 5-layer architectural graph and 8-step walkthrough for Google ADK (google/adk-python)

window.WALKTHROUGH_DATA = window.ADK_DATA = {
  repo: "google/adk-python",
  branch: "main",
  title: "google/adk-python",
  subtitle: "Google Agent Development Kit · Codebase Walkthrough",
  layers: [
    { id: "entry",        name: "Entry & CLI",             color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66, 133, 244, 0.08)" },
    { id: "engine",       name: "Execution Engine",        color: "#FBBC04", accent: "#FDD663", bg: "rgba(251, 188, 4, 0.08)" },
    { id: "agents",       name: "Agent Hierarchy",         color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255, 138, 101, 0.08)" },
    { id: "flows",        name: "Flows & Events",          color: "#34A853", accent: "#81C995", bg: "rgba(52, 168, 83, 0.08)" },
    { id: "capabilities", name: "Tools, Models & State",   color: "#A142F4", accent: "#C58AF9", bg: "rgba(161, 66, 244, 0.08)" }
  ],
  nodes: [
    // ROW 0: ENTRY & CLI (y = 26, x >= 200)
    {
      id: "init",
      label: "__init__.py",
      sub: "5 Core Exports",
      path: "src/google/adk/__init__.py",
      layer: "entry",
      lines: 39,
      x: 205, y: 26, w: 215, h: 58,
      role: "Top-level package entry point. Lazily exports the 5 core symbols of ADK: `Agent`, `Runner`, `Workflow`, `Context`, and `Event`.",
      snippet: `_LAZY_MEMBERS: dict[str, str] = {
    'Agent': '.agents.llm_agent',
    'Context': '.agents.context',
    'Event': '.events.event',
    'Runner': '.runners',
    'Workflow': '.workflow',
}
__all__ = ['Agent', 'Context', 'Event', 'Runner', 'Workflow']`
    },
    {
      id: "cli",
      label: "cli_tools_click.py",
      sub: "adk run · web · eval",
      path: "src/google/adk/cli/cli_tools_click.py",
      layer: "entry",
      lines: 1859,
      x: 495, y: 26, w: 215, h: 58,
      role: "Click-based CLI entry point powering `adk run`, `adk web`, `adk api_server`, `adk eval`, and `adk deploy`.",
      snippet: `@click.group()
def main():
  """Agent Development Kit CLI tools."""

@main.command("web")
def cli_web(agents_dir: str, port: int = 8000):
  app = get_fast_api_app(agents_dir=agents_dir, web=True)`
    },
    {
      id: "fastapi",
      label: "fast_api.py",
      sub: "Dev UI & SSE Server",
      path: "src/google/adk/cli/fast_api.py",
      layer: "entry",
      lines: 1471,
      x: 785, y: 26, w: 215, h: 58,
      role: "Builds the FastAPI application serving `/run_sse` (Server-Sent Events), session endpoints, and the browser Dev UI.",
      snippet: `@app.post("/run_sse")
async def run_agent_sse(req: RunAgentRequest) -> StreamingResponse:
  runner = await _get_runner_async(req.app_name)
  async def event_generator():
    async for event in runner.run_async(...):
      yield f"data: {event.model_dump_json()}\\n\\n"`
    },

    // ROW 1: EXECUTION ENGINE (y = 150, x >= 200)
    {
      id: "workflow",
      label: "_workflow.py",
      sub: "Workflow · Graph (ADK 2)",
      path: "src/google/adk/workflow/_workflow.py",
      layer: "engine",
      lines: 547,
      x: 205, y: 150, w: 215, h: 58,
      role: "ADK 2 graph workflow engine (`Workflow` & `Node`). Connects deterministic Python functions and LLM agents with explicit routing edges.",
      snippet: `class Workflow(Node):
  """A graph of nodes and edges for explicit orchestration."""
  nodes: Sequence[NodeSpecifier] = ()
  edges: Sequence[EdgeSpec] = ()`
    },
    {
      id: "runners",
      label: "runners.py",
      sub: "Runner · InMemoryRunner",
      path: "src/google/adk/runners.py",
      layer: "engine",
      lines: 1705,
      x: 495, y: 150, w: 215, h: 58,
      role: "Central runtime orchestrator. Loads the `Session`, constructs `InvocationContext`, streams `Event`s from `agent.run_async()`, and commits state deltas.",
      snippet: `class Runner:
  async def run_async(
      self, *, user_id: str, session_id: str, new_message: types.Content
  ) -> AsyncGenerator[Event, None]:
    session = await self.session_service.get_session(...)
    invocation_context = self._new_invocation_context(session, new_message)
    async for event in self.agent.run_async(invocation_context):
      await self.session_service.append_event(session=session, event=event)
      yield event`
    },
    {
      id: "inv_ctx",
      label: "invocation_context.py",
      sub: "InvocationContext",
      path: "src/google/adk/agents/invocation_context.py",
      layer: "engine",
      lines: 569,
      x: 785, y: 150, w: 215, h: 58,
      role: "Per-turn execution state created by `Runner` and passed through `Agent` → `Flow` → `Tool`. Holds `session`, services, and active `PluginManager`.",
      snippet: `class InvocationContext(BaseModel):
  artifact_service: Optional[BaseArtifactService] = None
  session_service: BaseSessionService
  memory_service: Optional[BaseMemoryService] = None
  session: Session
  agent: BaseAgent
  plugin_manager: PluginManager`
    },

    // ROW 2: AGENT HIERARCHY (y = 274, x >= 200)
    {
      id: "llm_agent",
      label: "llm_agent.py",
      sub: "LlmAgent (Agent)",
      path: "src/google/adk/agents/llm_agent.py",
      layer: "agents",
      lines: 1007,
      x: 200, y: 274, w: 188, h: 58,
      role: "The core LLM-powered agent (aliased as `Agent`). Configures `model`, `instruction`, `tools`, `output_schema`, and delegates execution to `BaseLlmFlow`.",
      snippet: `class LlmAgent(BaseAgent):
  model: Union[str, BaseLlm] = ''
  instruction: Union[str, InstructionProvider] = ''
  tools: list[ToolUnion] = Field(default_factory=list)

  async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    async for event in self._llm_flow.run_async(ctx):
      yield event

Agent: TypeAlias = LlmAgent`
    },
    {
      id: "base_agent",
      label: "base_agent.py",
      sub: "BaseAgent Contract",
      path: "src/google/adk/agents/base_agent.py",
      layer: "agents",
      lines: 794,
      x: 410, y: 274, w: 188, h: 58,
      role: "Abstract root class for every ADK agent. Manages the `sub_agents` hierarchy, before/after agent callbacks, and OpenTelemetry spans.",
      snippet: `class BaseAgent(BaseModel):
  name: str
  description: str = ''
  parent_agent: Optional[BaseAgent] = None
  sub_agents: list[BaseAgent] = Field(default_factory=list)

  @final
  async def run_async(self, parent_context: InvocationContext) -> AsyncGenerator[Event, None]:
    async for event in self._run_async_impl(ctx):
      yield event`
    },
    {
      id: "seq_agent",
      label: "sequential_agent.py",
      sub: "SequentialAgent",
      path: "src/google/adk/agents/sequential_agent.py",
      layer: "agents",
      lines: 120,
      x: 620, y: 274, w: 188, h: 58,
      role: "Deterministic shell agent that executes `sub_agents` one after another in order, sharing the same `InvocationContext`.",
      snippet: `class SequentialAgent(BaseAgent):
  async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    for sub_agent in self.sub_agents:
      async for event in sub_agent.run_async(ctx):
        yield event`
    },
    {
      id: "par_loop",
      label: "parallel & loop.py",
      sub: "Parallel · LoopAgent",
      path: "src/google/adk/agents/parallel_agent.py",
      layer: "agents",
      lines: 295,
      x: 830, y: 274, w: 188, h: 58,
      role: "Concurrent and iterative shell agents: `ParallelAgent` runs sub-agents simultaneously with isolated branch contexts; `LoopAgent` repeats until escalation or `max_iterations`.",
      snippet: `class ParallelAgent(BaseAgent):
  """Runs sub-agents concurrently in isolated branches."""

class LoopAgent(BaseAgent):
  """Repeats sub-agents until escalate=True or max_iterations."""`
    },

    // ROW 3: FLOWS & EVENTS (y = 398, x >= 200)
    {
      id: "base_flow",
      label: "base_llm_flow.py",
      sub: "BaseLlmFlow ReAct Loop",
      path: "src/google/adk/flows/llm_flows/base_llm_flow.py",
      layer: "flows",
      lines: 1293,
      x: 205, y: 398, w: 215, h: 58,
      role: "The ReAct engine. Runs request processors to build `LlmRequest`, calls the LLM, executes `FunctionTool` calls in `functions.py`, and loops until a final response.",
      snippet: `class BaseLlmFlow(ABC):
  async def run_async(self, invocation_context: InvocationContext) -> AsyncGenerator[Event, None]:
    while True:
      async for event in self._run_one_step_async(invocation_context):
        last_event = event
        yield event
      if not last_event or last_event.is_final_response():
        break`
    },
    {
      id: "auto_flow",
      label: "auto_flow.py",
      sub: "SingleFlow · AutoFlow",
      path: "src/google/adk/flows/llm_flows/auto_flow.py",
      layer: "flows",
      lines: 145,
      x: 495, y: 398, w: 215, h: 58,
      role: "Concrete flow pipeline combining modular request processors (`instructions`, `identity`, `contents`, `agent_transfer`) for multi-agent handoffs.",
      snippet: `class AutoFlow(SingleFlow):
  """SingleFlow with agent transfer capability across parent/peer/sub-agents."""
  def __init__(self):
    super().__init__()
    self.request_processors += [agent_transfer.request_processor]`
    },
    {
      id: "event",
      label: "event.py",
      sub: "Event · EventActions",
      path: "src/google/adk/events/event.py",
      layer: "flows",
      lines: 277,
      x: 785, y: 398, w: 215, h: 58,
      role: "Immutable record of every message, tool call, and `EventActions` (`state_delta`, `artifact_delta`, `transfer_to_agent`, `escalate`).",
      snippet: `class Event(LlmResponse):
  invocation_id: str = ''
  author: str
  actions: EventActions = Field(default_factory=EventActions)`
    },

    // ROW 4: TOOLS, MODELS & STATE (y = 522, x >= 200)
    {
      id: "tools",
      label: "function_tool.py",
      sub: "BaseTool · FunctionTool",
      path: "src/google/adk/tools/function_tool.py",
      layer: "capabilities",
      lines: 340,
      x: 200, y: 522, w: 188, h: 58,
      role: "Introspects Python functions (type annotations + docstrings) to auto-generate Gemini `FunctionDeclaration` schemas and execute tool calls.",
      snippet: `class FunctionTool(BaseTool):
  def __init__(self, func: Callable[..., Any]):
    super().__init__(name=func.__name__, description=func.__doc__)
    self.func = func`
    },
    {
      id: "models",
      label: "google_llm.py",
      sub: "BaseLlm · Gemini",
      path: "src/google/adk/models/google_llm.py",
      layer: "capabilities",
      lines: 615,
      x: 410, y: 522, w: 188, h: 58,
      role: "Concrete Gemini adapter (`google-genai` SDK) supporting Gemini API keys and Vertex AI, plus `LLMRegistry` model resolution.",
      snippet: `class Gemini(BaseLlm):
  model: str = 'gemini-2.5-flash'
  async def generate_content_async(
      self, llm_request: LlmRequest, stream: bool = False
  ) -> AsyncGenerator[LlmResponse, None]:`
    },
    {
      id: "sessions",
      label: "session_service.py",
      sub: "Session · Memory · State",
      path: "src/google/adk/sessions/base_session_service.py",
      layer: "capabilities",
      lines: 230,
      x: 620, y: 522, w: 188, h: 58,
      role: "Manages conversation `Session` persistence and applies `event.actions.state_delta` (supporting `user:`, `app:`, and `temp:` prefixes). Backed by InMemory, SQLite, Postgres, or Vertex AI.",
      snippet: `class BaseSessionService(ABC):
  async def append_event(self, session: Session, event: Event) -> Event:
    # Merges event.actions.state_delta into session.state`
    },
    {
      id: "eval_plugins",
      label: "agent_evaluator.py",
      sub: "Eval · Plugins · A2A",
      path: "src/google/adk/evaluation/agent_evaluator.py",
      layer: "capabilities",
      lines: 1039,
      x: 830, y: 522, w: 188, h: 58,
      role: "Production ecosystem: `AgentEvaluator` scores tool trajectories and responses; `PluginManager` runs global guardrails/tracing; `A2aAgentExecutor` exposes agents over A2A.",
      snippet: `class AgentEvaluator:
  """An evaluator for Agents, mainly intended for helping with test cases."""`
    }
  ],
  edges: [
    // Row 0 -> Row 1 & Row 0 horizontal (strictly non-crossing)
    { id: "init>workflow",        from: "init",       to: "workflow",   label: "exports Workflow",          detail: "`__init__.py` exports `Workflow` for ADK 2 graph orchestration." },
    { id: "init>runners",         from: "init",       to: "runners",    label: "exports Runner",            detail: "`__init__.py` exports `Runner` as the main execution entry point." },
    { id: "cli>runners",          from: "cli",        to: "runners",    label: "adk run",                   detail: "`adk run` creates a `Runner` and streams agent events in the terminal." },
    { id: "cli>fastapi",          from: "cli",        to: "fastapi",    label: "adk web",                   detail: "`adk web` launches the FastAPI server in `fast_api.py`." },
    { id: "fastapi>runners",      from: "fastapi",    to: "runners",    label: "/run_sse",                  detail: "`fast_api.py` calls `Runner.run_async()` and streams Events over SSE." },
    { id: "runners>inv_ctx",      from: "runners",    to: "inv_ctx",    label: "creates ctx",               detail: "`Runner` builds `InvocationContext` carrying the session, services, and plugin manager." },

    // Row 1 -> Row 2 & Row 2 horizontal (strictly non-crossing)
    { id: "workflow>llm_agent",   from: "workflow",   to: "llm_agent",  label: "schedules nodes",           detail: "`Workflow` orchestrates `LlmAgent` and deterministic function nodes across graph edges." },
    { id: "runners>base_agent",   from: "runners",    to: "base_agent", label: "agent.run_async(ctx)",      detail: "`Runner.run_async()` invokes `run_async(ctx)` on the root `BaseAgent`." },
    { id: "inv_ctx>par_loop",     from: "inv_ctx",    to: "par_loop",   label: "branch context",            detail: "`InvocationContext` isolates branch state for `ParallelAgent` and tracks `LoopAgent` iterations." },
    { id: "base_agent>llm_agent", from: "base_agent", to: "llm_agent",  label: "subclass",                  detail: "`LlmAgent` inherits lifecycle callbacks and tree hierarchy from `BaseAgent`." },
    { id: "base_agent>seq_agent", from: "base_agent", to: "seq_agent",  label: "subclass",                  detail: "`SequentialAgent` inherits from `BaseAgent`." },
    { id: "seq_agent>par_loop",   from: "seq_agent",  to: "par_loop",   label: "shell agents",              detail: "`SequentialAgent`, `ParallelAgent`, and `LoopAgent` form ADK's deterministic workflow shell agents." },

    // Row 2 -> Row 3 & Row 3 horizontal (strictly non-crossing)
    { id: "llm_agent>base_flow",  from: "llm_agent",  to: "base_flow",  label: "_llm_flow.run_async()",     detail: "`LlmAgent` delegates prompt building, model calling, and tool loops to `BaseLlmFlow`." },
    { id: "base_agent>auto_flow", from: "base_agent", to: "auto_flow",  label: "transfer_to_agent",         detail: "`AutoFlow` routes control across the `BaseAgent` parent/sub-agent hierarchy." },
    { id: "seq_agent>event",      from: "seq_agent",  to: "event",      label: "streams Events",            detail: "Shell agents yield sub-agent `Event`s upstream as each step completes." },
    { id: "par_loop>event",       from: "par_loop",   to: "event",      label: "escalate action",           detail: "`LoopAgent` watches `event.actions.escalate` to terminate loops cleanly." },
    { id: "base_flow>auto_flow",  from: "base_flow",  to: "auto_flow",  label: "processor pipeline",        detail: "`AutoFlow` and `SingleFlow` configure the request/response processors run by `BaseLlmFlow`." },
    { id: "auto_flow>event",      from: "auto_flow",  to: "event",      label: "yields Event",              detail: "Every model response, tool call, and agent transfer is emitted as an `Event`." },

    // Row 3 -> Row 4 (strictly non-crossing)
    { id: "base_flow>tools",      from: "base_flow",  to: "tools",      label: "tool.run_async()",          detail: "When the model emits a `function_call`, `BaseLlmFlow` executes `FunctionTool.run_async()` and loops." },
    { id: "base_flow>models",     from: "base_flow",  to: "models",     label: "generate_content_async()",  detail: "`BaseLlmFlow` calls `Gemini.generate_content_async(llm_request)`." },
    { id: "auto_flow>models",     from: "auto_flow",  to: "models",     label: "LlmRequest",                detail: "`AutoFlow`'s request processors assemble the `LlmRequest` sent to the model backend." },
    { id: "event>sessions",       from: "event",      to: "sessions",   label: "state_delta",               detail: "`Event.actions.state_delta` updates `session.state` when persisted by `SessionService`." },
    { id: "event>eval_plugins",   from: "event",      to: "eval_plugins",label: "evaluates trajectory",     detail: "`AgentEvaluator` inspects emitted `Event` trajectories to score tool use and final responses." }
  ],
  walkthrough: [
    {
      step: 1,
      title: "The Front Door: `__init__.py`",
      focusNode: "init",
      activeNodes: ["init", "llm_agent", "workflow", "runners", "inv_ctx", "event"],
      activeEdges: ["init>workflow", "init>runners", "runners>inv_ctx", "workflow>llm_agent"],
      cues: [
        { at: 0.00, nodes: ["init"], focus: "init" },
        { at: 0.22, nodes: ["llm_agent"], focus: "llm_agent" },
        { at: 0.37, nodes: ["workflow"], focus: "workflow" },
        { at: 0.51, nodes: ["runners"], focus: "runners" },
        { at: 0.65, nodes: ["inv_ctx"], focus: "inv_ctx" },
        { at: 0.77, nodes: ["event"], focus: "event" },
        { at: 0.88, nodes: ["init", "llm_agent", "workflow", "runners", "inv_ctx", "event"], focus: "init" }
      ],
      audio: "audio/step-1.wav",
      summary: "`src/google/adk/__init__.py` exposes the **5 core primitives** of the framework: `Agent` (`llm_agent.py`), `Workflow` (`_workflow.py`), `Runner` (`runners.py`), `Context` (`invocation_context.py`), and `Event` (`event.py`).",
      narration: "At the top of the codebase, init.py exposes just five core building blocks: Agent in llm agent.py, Workflow in workflow.py, Runner in runners.py, Context in invocation context.py, and Event in event.py. Every other module in the repository plugs into these five primitives."
    },
    {
      step: 2,
      title: "CLI & Web Server: `cli_tools_click.py` & `fast_api.py`",
      focusNode: "cli",
      activeNodes: ["cli", "fastapi", "runners"],
      activeEdges: ["cli>fastapi", "cli>runners", "fastapi>runners"],
      cues: [
        { at: 0.00, node: "cli" },
        { at: 0.48, node: "fastapi" },
        { at: 0.78, node: "runners" }
      ],
      audio: "audio/step-2.wav",
      summary: "Running `adk run` or `adk web` starts in `cli_tools_click.py`. The Dev UI and Cloud Run server (`fast_api.py`) wrap `runners.py` and stream events over Server-Sent Events (`/run_sse`).",
      narration: "Command line execution starts in cli tools click.py, which powers adk run, adk web, and adk eval. When you launch the web interface, fast api.py spins up a FastAPI server that calls runners.py and streams events over Server-Sent Events."
    },
    {
      step: 3,
      title: "The Execution Engine: `runners.py` & `invocation_context.py`",
      focusNode: "runners",
      activeNodes: ["runners", "inv_ctx", "base_agent"],
      activeEdges: ["runners>inv_ctx", "runners>base_agent"],
      cues: [
        { at: 0.00, node: "runners" },
        { at: 0.42, node: "inv_ctx" },
        { at: 0.74, node: "base_agent" }
      ],
      audio: "audio/step-3.wav",
      summary: "`Runner.run_async()` in `runners.py` is the central orchestrator. On each turn it loads the session, constructs an `InvocationContext` (`invocation_context.py`), and invokes `run_async(ctx)` on the root `BaseAgent` (`base_agent.py`).",
      narration: "Inside the execution engine, runners.py orchestrates each turn of a conversation. It constructs an Invocation Context in invocation context.py to hold the active session and services, and then calls run async on the root agent in base agent.py."
    },
    {
      step: 4,
      title: "Agents & Hierarchy: `base_agent.py` & `llm_agent.py`",
      focusNode: "base_agent",
      activeNodes: ["base_agent", "llm_agent", "base_flow"],
      activeEdges: ["base_agent>llm_agent", "llm_agent>base_flow"],
      cues: [
        { at: 0.00, node: "base_agent" },
        { at: 0.44, node: "llm_agent" },
        { at: 0.78, node: "base_flow" }
      ],
      audio: "audio/step-4.wav",
      summary: "All agents inherit from `BaseAgent` (`base_agent.py`), which manages sub-agent trees, callbacks, and tracing. `LlmAgent` (`llm_agent.py`, aliased as `Agent`) configures the model, instructions, and tools, and delegates execution to `base_llm_flow.py`.",
      narration: "Every agent in ADK inherits from base agent.py, which manages sub-agent hierarchies, lifecycle callbacks, and tracing spans. For model-backed agents, llm agent.py configures instructions and tools, and delegates the reasoning loop to base llm flow.py."
    },
    {
      step: 5,
      title: "Deterministic Orchestration: `_workflow.py` & Shell Agents",
      focusNode: "workflow",
      activeNodes: ["workflow", "llm_agent", "base_agent", "seq_agent", "par_loop"],
      activeEdges: ["workflow>llm_agent", "base_agent>seq_agent", "seq_agent>par_loop"],
      cues: [
        { at: 0.00, node: "seq_agent" },
        { at: 0.30, node: "par_loop" },
        { at: 0.60, node: "workflow" },
        { at: 0.84, node: "llm_agent" }
      ],
      audio: "audio/step-5.wav",
      summary: "For predictable multi-step pipelines, use shell agents (`sequential_agent.py` and `parallel & loop.py` under `base_agent.py`) or ADK 2's `Workflow` (`_workflow.py`), which wires deterministic Python nodes and `llm_agent.py` in an explicit graph.",
      narration: "When you want deterministic orchestration instead of model-driven routing, sequential agent.py and parallel and loop.py execute sub-agents in strict order, concurrency, or loops. And workflow.py wires deterministic Python functions and llm agent.py into an explicit graph."
    },
    {
      step: 6,
      title: "The ReAct Loop: `base_llm_flow.py` & `auto_flow.py`",
      focusNode: "base_flow",
      activeNodes: ["llm_agent", "base_flow", "auto_flow", "event"],
      activeEdges: ["llm_agent>base_flow", "base_flow>auto_flow", "auto_flow>event"],
      cues: [
        { at: 0.00, node: "base_flow" },
        { at: 0.34, node: "auto_flow" },
        { at: 0.74, node: "event" }
      ],
      audio: "audio/step-6.wav",
      summary: "`base_llm_flow.py` and `auto_flow.py` run modular request processors (`instructions`, `contents`, `agent_transfer`) to build `LlmRequest`, call the LLM, execute tool calls, and emit each turn step through `event.py`.",
      narration: "Under the hood, base llm flow.py and auto flow.py drive the ReAct reasoning loop. They run modular request processors to assemble the prompt, coordinate sub-agent transfers, and emit every model response and tool call through event.py."
    },
    {
      step: 7,
      title: "Tools & Model Backends: `function_tool.py` & `google_llm.py`",
      focusNode: "tools",
      activeNodes: ["base_flow", "auto_flow", "tools", "models"],
      activeEdges: ["base_flow>tools", "base_flow>models", "auto_flow>models"],
      cues: [
        { at: 0.00, node: "tools" },
        { at: 0.56, node: "models" }
      ],
      audio: "audio/step-7.wav",
      summary: "During each flow turn (`base_llm_flow.py` & `auto_flow.py`), `function_tool.py` inspects Python type hints and docstrings to generate Gemini tool declarations, while `google_llm.py` connects flows to the Gemini API and Vertex AI.",
      narration: "During each turn of the flow, function tool.py inspects your Python type hints and docstrings to build tool schemas and run functions automatically, while google llm.py connects your agents to Gemini and Vertex AI."
    },
    {
      step: 8,
      title: "Event-Driven State & Evaluation: `event.py`, `session_service.py` & `agent_evaluator.py`",
      focusNode: "event",
      activeNodes: ["auto_flow", "event", "sessions", "eval_plugins"],
      activeEdges: ["auto_flow>event", "event>sessions", "event>eval_plugins"],
      cues: [
        { at: 0.00, node: "event" },
        { at: 0.42, node: "sessions" },
        { at: 0.72, node: "eval_plugins" }
      ],
      audio: "audio/step-8.wav",
      summary: "Agents never mutate databases directly—they attach `state_delta` to `event.py`, which `session_service.py` persists. Finally, `agent_evaluator.py` scores emitted event trajectories against test cases.",
      narration: "Finally, state in ADK is event-driven: agents attach state deltas to event.py, which session service.py persists across turns. And agent evaluator.py scores those emitted event trajectories against test cases."
    }
  ]
};
