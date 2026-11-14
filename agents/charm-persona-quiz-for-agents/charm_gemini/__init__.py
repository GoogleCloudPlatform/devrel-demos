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

"""CHARM — Google Gemini Decision 1 (gemini-decision-1 · /v1beta/decisions) OCEAN Personality Client."""

from .client import (
    FLOW_FORMAT_C_PERSONAS,
    OCEAN_TRAITS,
    build_decisions_request,
    build_systemone_request,
    call_gemini_decisions_api,
    resolve_format_c_persona,
    verify_gemini_decisions_sdk,
)

__all__ = [
    "FLOW_FORMAT_C_PERSONAS",
    "OCEAN_TRAITS",
    "build_decisions_request",
    "build_systemone_request",
    "call_gemini_decisions_api",
    "resolve_format_c_persona",
    "verify_gemini_decisions_sdk",
]
