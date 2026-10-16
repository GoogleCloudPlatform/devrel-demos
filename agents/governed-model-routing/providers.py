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

"""Model adapters for Gemini and Claude on Gemini Enterprise Agent Platform.

One provider-neutral transcript, two renderers. The rule that makes cross-model routing work:
reasoning artifacts (Gemini thought signatures, Claude thinking blocks) are replayed only to
the exact model that produced them. Steps produced by another model are replayed as plain
tool calls: Gemini needs the documented placeholder signature on them, Claude needs nothing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types

# Documented escape hatch for function calls the target Gemini model did not generate itself.
PLACEHOLDER_SIGNATURE = b"skip_thought_signature_validator"
GEMINI_MAX_OUTPUT_TOKENS = 32_000
# The Anthropic SDK requires streaming above ~21K max_tokens (its 10-minute non-streaming guard);
# 16K covers one agent turn (thinking + tool call) comfortably.
CLAUDE_MAX_TOKENS = 16_000


@dataclass(frozen=True)
class ModelSpec:
    """`MODEL_ID[:LEVEL]`, e.g. `gemini-3.8-flash:low` or `claude-opus-5-5:high`."""
    model_id: str
    level: str | None = None

    @property
    def provider(self) -> str:
        return "claude" if self.model_id.startswith("claude-") else "gemini"

    def __str__(self) -> str:
        return self.model_id + (f":{self.level}" if self.level else "")


def parse_spec(spec: str) -> ModelSpec:
    model_id, _, level = spec.strip().partition(":")
    if not model_id:
        raise ValueError("empty model spec")
    return ModelSpec(model_id, level.strip().lower() or None)


@dataclass
class Usage:
    """Token usage normalized across providers."""
    input_uncached: int = 0
    cache_read: int = 0
    cache_write: int = 0  # Claude explicit cache writes; always 0 for Gemini
    output: int = 0       # includes thinking tokens (billed as output)
    thinking: int = 0

    @property
    def prompt_tokens(self) -> int:
        return self.input_uncached + self.cache_read + self.cache_write


@dataclass
class ToolSpec:
    name: str
    description: str
    schema: dict


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class UserText:
    text: str


@dataclass
class Step:
    """One model response in provider-neutral form."""
    model: str                      # exact model id that produced it
    text: str
    calls: list[ToolCall]
    usage: Usage
    native: Any = None              # Gemini Content or Claude content blocks; replayed only to `model`
    latency_s: float = 0.0
    finish_reason: str = ""


@dataclass
class ToolResults:
    results: list[tuple[ToolCall, str]] = field(default_factory=list)


Transcript = list  # of UserText | Step | ToolResults


class GeminiModel:
    def __init__(self, spec: ModelSpec, project: str, location: str = "global", client: Any = None):
        self.spec = spec
        self.client = client or genai.Client(
            enterprise=True, project=project, location=location,
            http_options=types.HttpOptions(
                timeout=600_000,
                retry_options=types.HttpRetryOptions(
                    attempts=6, initial_delay=2.0, max_delay=60.0,
                    http_status_codes=[429, 500, 502, 503, 504])))

    async def step(self, system: str, tools: list[ToolSpec], transcript: Transcript) -> Step:
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        if tools:
            config.tools = [types.Tool(function_declarations=[
                types.FunctionDeclaration(name=t.name, description=t.description, parameters_json_schema=t.schema)
                for t in tools])]
        if self.spec.level:
            config.thinking_config = types.ThinkingConfig(thinking_level=self.spec.level.upper())
        started = time.monotonic()
        resp = await self.client.aio.models.generate_content(
            model=self.spec.model_id, contents=self.render(transcript), config=config)
        candidate = resp.candidates[0] if resp.candidates else None
        content = candidate.content if candidate and candidate.content else None
        parts = (content.parts or []) if content else []
        calls = [ToolCall(id=p.function_call.id or f"g{i}_{int(started * 1000) % 10**8}",
                          name=p.function_call.name or "", args=dict(p.function_call.args or {}))
                 for i, p in enumerate(parts) if p.function_call]
        u = resp.usage_metadata or types.GenerateContentResponseUsageMetadata()
        prompt, cached, thoughts = u.prompt_token_count or 0, u.cached_content_token_count or 0, u.thoughts_token_count or 0
        usage = Usage(input_uncached=prompt - cached, cache_read=cached,
                      output=(u.candidates_token_count or 0) + thoughts, thinking=thoughts)
        return Step(model=self.spec.model_id,
                    text="".join(p.text for p in parts if p.text and not p.thought),
                    calls=calls, usage=usage, native=content if parts else None,
                    latency_s=round(time.monotonic() - started, 2),
                    finish_reason=str(candidate.finish_reason) if candidate and candidate.finish_reason else "")

    def render(self, transcript: Transcript) -> list[types.Content]:
        out: list[types.Content] = []
        for item in transcript:
            if isinstance(item, UserText):
                out.append(types.Content(role="user", parts=[types.Part.from_text(text=item.text)]))
            elif isinstance(item, Step):
                if item.model == self.spec.model_id and item.native is not None:
                    out.append(item.native)  # own turn: thought signatures intact
                    continue
                parts = [types.Part.from_text(text=item.text)] if item.text else []
                parts += [types.Part(function_call=types.FunctionCall(name=c.name, args=c.args),
                                     thought_signature=PLACEHOLDER_SIGNATURE) for c in item.calls]
                if parts:
                    out.append(types.Content(role="model", parts=parts))
            elif isinstance(item, ToolResults) and item.results:
                out.append(types.Content(role="user", parts=[
                    types.Part(function_response=types.FunctionResponse(name=c.name, response={"output": text}))
                    for c, text in item.results]))
        return out

    async def aclose(self) -> None:
        try:
            await self.client.aio.aclose()
        except Exception:  # best effort during shutdown
            pass


class ClaudeModel:
    def __init__(self, spec: ModelSpec, project: str, region: str = "global", client: Any = None):
        self.spec = spec
        if client is None:
            from anthropic import AsyncAnthropicVertex  # only needed when a Claude model is chosen
            client = AsyncAnthropicVertex(project_id=project, region=region, max_retries=6)
        self.client = client

    async def step(self, system: str, tools: list[ToolSpec], transcript: Transcript) -> Step:
        kwargs: dict[str, Any] = {}
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.schema} for t in tools]
        if self.spec.level:
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": self.spec.level}
        started = time.monotonic()
        resp = await self.client.messages.create(
            model=self.spec.model_id, max_tokens=CLAUDE_MAX_TOKENS, system=system,
            messages=self.render(transcript),
            cache_control={"type": "ephemeral"},  # rolling cache marker on the last cacheable block
            **kwargs)
        u = resp.usage
        details = getattr(u, "output_tokens_details", None)
        usage = Usage(input_uncached=u.input_tokens or 0, cache_read=u.cache_read_input_tokens or 0,
                      cache_write=u.cache_creation_input_tokens or 0, output=u.output_tokens or 0,
                      thinking=(details.thinking_tokens if details else 0) or 0)
        blocks = [b.model_dump(exclude_none=True) for b in resp.content]
        return Step(model=self.spec.model_id,
                    text="".join(b.text for b in resp.content if b.type == "text"),
                    calls=[ToolCall(id=b.id, name=b.name, args=dict(b.input))
                           for b in resp.content if b.type == "tool_use"],
                    usage=usage, native=blocks or None,
                    latency_s=round(time.monotonic() - started, 2), finish_reason=resp.stop_reason or "")

    def render(self, transcript: Transcript) -> list[dict]:
        messages: list[dict] = []

        def add(role: str, blocks: list[dict]) -> None:
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"].extend(blocks)  # merge consecutive same-role turns
            else:
                messages.append({"role": role, "content": list(blocks)})

        for item in transcript:
            if isinstance(item, UserText):
                add("user", [{"type": "text", "text": item.text}])
            elif isinstance(item, Step):
                if not (item.text or item.calls):
                    continue
                if item.model == self.spec.model_id and item.native:
                    add("assistant", item.native)  # own turn: thinking blocks + signatures intact
                    continue
                blocks = [{"type": "text", "text": item.text}] if item.text else []
                blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.args} for c in item.calls]
                add("assistant", blocks)
            elif isinstance(item, ToolResults) and item.results:
                add("user", [{"type": "tool_result", "tool_use_id": c.id, "content": text}
                             for c, text in item.results])
        return messages

    async def aclose(self) -> None:
        try:
            await self.client.close()
        except Exception:  # best effort during shutdown
            pass


def make_model(spec: ModelSpec, project: str, location: str = "global") -> GeminiModel | ClaudeModel:
    cls = ClaudeModel if spec.provider == "claude" else GeminiModel
    return cls(spec, project, location)
