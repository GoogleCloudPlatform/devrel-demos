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

import pytest
from hawker_queue import HawkerQueueEngine, Order

def test_standard_wait_time():
    orders = [Order("1", 5.0), Order("2", 6.0)]
    engine = HawkerQueueEngine(orders)
    assert engine.calculate_wait_time() == 6.0

def test_custom_order_multiplier():
    orders = [Order("1", 5.0, customizations=["extra chili"])]
    engine = HawkerQueueEngine(orders)
    assert engine.calculate_wait_time() == 4.5

def test_chope_tissue_priority():
    orders = [Order("1", 5.0)]
    engine = HawkerQueueEngine(orders, table_status="choped_with_tissue_pack")
    assert engine.calculate_wait_time() == 2.0

def test_surge_pricing_hard_cap():
    orders = [Order(str(i), 5.0) for i in range(25)]
    engine = HawkerQueueEngine(orders)
    assert engine.calculate_surge_multiplier() == 1.5
    assert engine.calculate_order_price(orders[0]) == 7.5

def test_negative_queue_raises_value_error():
    with pytest.raises(ValueError):
        Order("1", -5.0)

def test_sgd_currency_rounding():
    order = Order("1", 5.555)
    orders = [order] * 12
    engine = HawkerQueueEngine(orders)
    assert engine.calculate_order_price(order) == round(5.555 * 1.2, 2)
