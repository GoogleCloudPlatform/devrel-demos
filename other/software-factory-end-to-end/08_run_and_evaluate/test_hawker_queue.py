# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for Hawker Food Queue Wait Time and Pricing Calculator."""

import pytest
from hawker_queue import Order, calculate_wait_time, calculate_surge_price


def test_standard_order_wait_time():
    orders = [Order("1", 5.0), Order("2", 6.0)]
    assert calculate_wait_time(orders) == 6.0


def test_custom_order_wait_time():
    orders = [Order("1", 5.0, is_custom=True)]
    assert calculate_wait_time(orders) == 4.5


def test_empty_queue_wait_time():
    assert calculate_wait_time([]) == 0.0


def test_standard_pricing_no_surge():
    assert calculate_surge_price(10.0, queue_length=3) == 10.0


def test_surge_pricing_applied():
    assert calculate_surge_price(10.0, queue_length=8) == 12.0


def test_negative_values_raise_value_error():
    with pytest.raises(ValueError):
        Order("1", -5.0)
    with pytest.raises(ValueError):
        calculate_surge_price(-10.0, queue_length=3)
    with pytest.raises(ValueError):
        calculate_surge_price(10.0, queue_length=-1)
