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
 * @description Package initializer for dependency-injected cloud services, Memory Bank,
 *   and Agent2Agent (A2A) protocol utilities.
 *
 * Why: Re-exports service protocols, offline-capable implementations, and A2A builders
 * from `pitch_generator.app_utils` so both the starter app and `.agents/solutions/`
 * modules share a single clean interface layer.
 */
"""

from __future__ import annotations

from pitch_generator.app_utils.a2a import (
    AGENT_CARD_WELL_KNOWN_PATH,
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
    AgentCardBuilder,
    DefaultRequestHandler,
    TaskState,
    attach_a2a_routes,
    include_artifacts_in_a2a_event_interceptor,
)
from pitch_generator.app_utils.memory_bank import MemoryBankService, MemoryEntry
from pitch_generator.app_utils.services import (
    MINIMAL_PNG_BYTES,
    ArtifactRecord,
    ArtifactServiceProtocol,
    BigQueryAnalyticsService,
    DeterministicMockLLMClient,
    EnterpriseGenAILLMClient,
    GcsArtifactService,
    InMemoryArtifactService,
    LLMClientProtocol,
    MockLLMClient,
    ServiceContainer,
    get_artifact_service,
    get_default_services,
)

__all__ = [
    "AGENT_CARD_WELL_KNOWN_PATH",
    "A2aAgentExecutor",
    "A2aAgentExecutorConfig",
    "AgentCardBuilder",
    "DefaultRequestHandler",
    "TaskState",
    "attach_a2a_routes",
    "include_artifacts_in_a2a_event_interceptor",
    "MemoryBankService",
    "MemoryEntry",
    "MINIMAL_PNG_BYTES",
    "ArtifactRecord",
    "ArtifactServiceProtocol",
    "BigQueryAnalyticsService",
    "DeterministicMockLLMClient",
    "EnterpriseGenAILLMClient",
    "GcsArtifactService",
    "InMemoryArtifactService",
    "LLMClientProtocol",
    "MockLLMClient",
    "ServiceContainer",
    "get_artifact_service",
    "get_default_services",
]
