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

"""
/**
 * @file __init__.py
 * @description Package initializer for the Pitch Generator multi-agent backend.
 *
 * Why: Exposes top-level configuration, specialist agent factories, structured
 * payload models, `LoopGuard`, agent workflow entrypoints, and version metadata
 * so callers and ADK/agents-cli tooling can import `pitch_generator` directly
 * without coupling to internal submodule paths.
 */
"""

from __future__ import annotations

from pitch_generator.agent import (
    IMAGE_MODEL,
    MODEL,
    SPECIALIST_AGENTS,
    Agent,
    App,
    ArtDirectionPayload,
    CampaignConcept,
    CircularLoopError,
    ConceptPayload,
    Context,
    CopyPayload,
    Event,
    Gemini,
    JoinNode,
    LoopGuard,
    PayloadValidationError,
    PitchPackage,
    RemoteA2aAgent,
    RequestInput,
    VisualPayload,
    Workflow,
    app,
    assemble,
    brand_strategist,
    build_specialist_team,
    copywriter,
    create_specialist_agents,
    creative_director,
    execute_specialists,
    execute_workflow,
    extract_json_payload,
    generate_key_visual,
    get_specialist_agent,
    get_specialist_agents,
    loop_guard,
    node,
    package,
    parse_json_payload,
    parse_payload,
    resume_pitch_workflow,
    root_agent,
    run_graph_workflow,
    run_pitch_workflow,
    run_specialist_team,
    run_specialists,
    run_workflow,
    strip_markdown_fences,
    types,
    visual_director,
)
from pitch_generator.config import ConfigurationError, PitchConfig, get_config, normalize_bucket_name

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "ConfigurationError",
    "PitchConfig",
    "get_config",
    "normalize_bucket_name",
    "MODEL",
    "IMAGE_MODEL",
    "SPECIALIST_AGENTS",
    "Agent",
    "App",
    "ArtDirectionPayload",
    "CampaignConcept",
    "CircularLoopError",
    "ConceptPayload",
    "Context",
    "CopyPayload",
    "Event",
    "Gemini",
    "JoinNode",
    "LoopGuard",
    "PayloadValidationError",
    "PitchPackage",
    "RemoteA2aAgent",
    "RequestInput",
    "VisualPayload",
    "Workflow",
    "app",
    "root_agent",
    "creative_director",
    "copywriter",
    "brand_strategist",
    "visual_director",
    "build_specialist_team",
    "create_specialist_agents",
    "get_specialist_agents",
    "get_specialist_agent",
    "run_specialist_team",
    "execute_specialists",
    "run_specialists",
    "generate_key_visual",
    "assemble",
    "package",
    "loop_guard",
    "node",
    "strip_markdown_fences",
    "parse_json_payload",
    "parse_payload",
    "extract_json_payload",
    "run_graph_workflow",
    "execute_workflow",
    "run_workflow",
    "run_pitch_workflow",
    "resume_pitch_workflow",
    "types",
]
