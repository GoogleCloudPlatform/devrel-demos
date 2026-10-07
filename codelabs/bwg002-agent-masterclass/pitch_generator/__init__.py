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
 * Why: Exposes top-level configuration, agent workflow entrypoints, and version
 * metadata so callers and ADK/agents-cli tooling can import `pitch_generator`
 * directly without coupling to internal submodule paths.
 */
"""

from __future__ import annotations

from pitch_generator.agent import (
    app,
    assemble,
    copywriter,
    creative_director,
    package,
    resume_pitch_workflow,
    root_agent,
    run_pitch_workflow,
    select_routing_decision,
)
from pitch_generator.config import ConfigurationError, PitchConfig, get_config, normalize_bucket_name

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "ConfigurationError",
    "PitchConfig",
    "get_config",
    "normalize_bucket_name",
    "app",
    "root_agent",
    "creative_director",
    "copywriter",
    "assemble",
    "package",
    "select_routing_decision",
    "run_pitch_workflow",
    "resume_pitch_workflow",
]
