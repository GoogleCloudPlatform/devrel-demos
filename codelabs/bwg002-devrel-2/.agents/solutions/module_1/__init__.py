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
 * @description Package initializer for Module 1 ("Expand the agent team") reference solutions.
 *
 * Why: Exposes step metadata for Module 1 Steps 1a through 1c (Authoring Agent Skills,
 * Skill Evals, and Remote Visual Director over A2A) so learners and verification tools
 * can locate each progressive enhancement cleanly.
 */
"""

from __future__ import annotations

MODULE_ID: int = 1
MODULE_TITLE: str = "Expand the agent team"
MODULE_1_STEPS: tuple[str, ...] = ("1a", "1b", "1c")

__all__ = ["MODULE_ID", "MODULE_TITLE", "MODULE_1_STEPS"]
