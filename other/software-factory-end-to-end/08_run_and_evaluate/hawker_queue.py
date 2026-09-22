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

"""Reference implementation for Hawker Food Queue Wait Time and Pricing Calculator."""

from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    base_price: float
    is_custom: bool = False

    def __post_init__(self):
        if self.base_price < 0:
            raise ValueError("base_price cannot be negative")
        if self.base_price > 100.0:
            raise ValueError("base_price exceeds maximum allowed 100.0")


def calculate_wait_time(orders: list[Order]) -> float:
    """Calculate total wait time in minutes.

    Standard orders take 3.0 minutes. Custom orders take 4.5 minutes (3.0 * 1.5).
    """
    total = 0.0
    for order in orders:
        total += 4.5 if order.is_custom else 3.0
    return round(total, 2)


def calculate_surge_price(base_price: float, queue_length: int) -> float:
    """Calculate price with queue surge multiplier.

    - queue_length <= 5: 1.0x (standard price)
    - queue_length > 5:  1.2x (peak surge price)
    Raises ValueError if queue_length < 0 or base_price < 0.
    """
    if queue_length < 0:
        raise ValueError("queue_length cannot be negative")
    if base_price < 0:
        raise ValueError("base_price cannot be negative")

    multiplier = 1.2 if queue_length > 5 else 1.0
    return round(base_price * multiplier, 2)
