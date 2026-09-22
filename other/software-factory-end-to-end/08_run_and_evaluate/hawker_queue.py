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

"""Reference implementation for Starlight Hainan Kitchen Queue & Surge Engine."""

from dataclasses import dataclass, field
from typing import List

@dataclass
class Order:
    order_id: str
    base_price_sgd: float
    customizations: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.base_price_sgd < 0:
            raise ValueError("base_price_sgd cannot be negative")
        if self.base_price_sgd > 100.0:
            raise ValueError("base_price_sgd exceeds maximum allowed 100.0 SGD")

class HawkerQueueEngine:
    def __init__(self, orders: List[Order] = None, table_status: str = "open"):
        self.orders = orders or []
        self.table_status = table_status
        if len(self.orders) < 0:
            raise ValueError("Queue length cannot be negative")

    def calculate_wait_time(self) -> float:
        total_time = 0.0
        for o in self.orders:
            prep = 3.0
            if any(c in ['extra chili', 'no skin'] for c in o.customizations):
                prep *= 1.5
            total_time += prep

        if self.table_status == "choped_with_tissue_pack":
            total_time = max(0.0, total_time - 1.0)

        return round(total_time, 2)

    def calculate_surge_multiplier(self) -> float:
        q_len = len(self.orders)
        if q_len <= 10:
            return 1.0
        elif q_len <= 20:
            return 1.2
        else:
            return 1.5

    def calculate_order_price(self, order: Order) -> float:
        multiplier = self.calculate_surge_multiplier()
        final_price = order.base_price_sgd * multiplier
        return round(final_price, 2)
