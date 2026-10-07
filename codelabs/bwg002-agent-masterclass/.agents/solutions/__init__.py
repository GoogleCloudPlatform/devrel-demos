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
 * @description Package initializer for the Pitch Generator hidden reference solutions.
 *
 * Why: Organizes progressive reference implementations across Modules 1 through 4
 * (`1a`-`1e`, `2a`-`2c`, `3a`-`3c`, `4a`-`4b`) so the `lab-helper` skill and automated
 * E2E verification suite can inspect, diff, and remediate any individual lab step
 * deterministically offline.
 */
"""

from __future__ import annotations

MODULES: tuple[str, ...] = ("module_1", "module_2", "module_3", "module_4")
STEPS: tuple[str, ...] = (
    "1a",
    "1b",
    "1c",
    "1d",
    "1e",
    "2a",
    "2b",
    "2c",
    "3a",
    "3b",
    "3c",
    "4a",
    "4b",
)

__all__ = ["MODULES", "STEPS"]
