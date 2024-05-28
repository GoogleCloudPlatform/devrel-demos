#!/usr/bin/env python

# Copyright 2024 Google LLC.
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

from lib.system_health import get_system_health


def test_get_system_health():
    hc = get_system_health()

    # check key names
    assert "CPU" in hc
    assert "MEMORY" in hc

    # check values are less than 1 (expected fractional valbe between 0 and 1)
    assert 0.0 <= hc["CPU"] <= 100.0
    assert 0.0 <= hc["MEMORY"] <= 100.0
