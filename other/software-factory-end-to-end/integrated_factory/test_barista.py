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

"""Unit tests for Byte & Brew Smart Barista Order & Pricing Engine."""

import pytest
from barista import DrinkOrder, calculate_drink_price, calculate_caffeine_mg


def test_standard_medium_latte():
    order = DrinkOrder(size="medium")
    assert calculate_drink_price(order) == 4.50
    assert calculate_caffeine_mg(order) == 75


def test_plant_milk_and_syrup_surcharge():
    order = DrinkOrder(size="small", milk="oat", syrups=["vanilla"])
    # 3.50 + 0.75 (oat) + 0.50 (vanilla) = 4.75
    assert calculate_drink_price(order) == 4.75


def test_extra_shots_pricing_and_caffeine():
    order = DrinkOrder(size="large", extra_shots=2)
    # 5.25 + 2.00 (extra shots) = 7.25
    assert calculate_drink_price(order) == 7.25
    # (1 base + 2 extra) * 75mg = 225mg
    assert calculate_caffeine_mg(order) == 225


def test_decaf_caffeine_calculation():
    order = DrinkOrder(size="small", extra_shots=1, is_decaf=True)
    # (1 base + 1 extra) * 5mg = 10mg
    assert calculate_caffeine_mg(order) == 10


def test_invalid_drink_size_raises_value_error():
    with pytest.raises(ValueError):
        DrinkOrder(size="extra_huge")


def test_excessive_shots_safety_cap():
    with pytest.raises(ValueError):
        DrinkOrder(size="medium", extra_shots=6)
    with pytest.raises(ValueError):
        DrinkOrder(size="small", extra_shots=-1)
