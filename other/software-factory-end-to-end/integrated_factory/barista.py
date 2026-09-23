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

"""Reference implementation for Byte & Brew Smart Barista Order & Pricing Engine."""

from dataclasses import dataclass, field
from typing import List


BASE_PRICES = {
    "small": 3.50,
    "medium": 4.50,
    "large": 5.25,
}

PLANT_MILKS = {"oat", "almond", "soy"}


@dataclass
class DrinkOrder:
    size: str
    milk: str = "whole"
    extra_shots: int = 0
    syrups: List[str] = field(default_factory=list)
    is_decaf: bool = False

    def __post_init__(self):
        self.size = self.size.lower()
        self.milk = self.milk.lower()
        if self.size not in BASE_PRICES:
            raise ValueError(f"Invalid size '{self.size}'. Choose from: small, medium, large.")
        if self.extra_shots < 0:
            raise ValueError("extra_shots cannot be negative.")
        if self.extra_shots > 5:
            raise ValueError("Maximum 5 extra shots allowed per drink for safety.")


def calculate_drink_price(order: DrinkOrder) -> float:
    """Calculate the total price of a drink order in USD.

    - Base price: small ($3.50), medium ($4.50), large ($5.25).
    - Plant milk surcharge: +$0.75 for oat, almond, or soy.
    - Extra espresso shots: +$1.00 each.
    - Syrups: +$0.50 per flavor pump.
    """
    total = BASE_PRICES[order.size]

    if order.milk in PLANT_MILKS:
        total += 0.75

    total += order.extra_shots * 1.00
    total += len(order.syrups) * 0.50

    return round(total, 2)


def calculate_caffeine_mg(order: DrinkOrder) -> int:
    """Calculate the estimated caffeine content in milligrams.

    - Standard drink includes 1 base espresso shot + extra_shots.
    - Regular espresso: 75 mg per shot.
    - Decaf: 5 mg per shot.
    """
    total_shots = 1 + order.extra_shots
    mg_per_shot = 5 if order.is_decaf else 75
    return total_shots * mg_per_shot
