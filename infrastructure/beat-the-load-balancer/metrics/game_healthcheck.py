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

import json
from typing import Union


class GameHealthcheck:
    """
    message = {
        "datetime": _datetime,                # Time-stamp denoting the message creation time at VM (ISO 8601)
        "cpu": cpu,                           # Current CPU utilization rate in the VM
        "memory": memory,                     # Current memory consumption in the VM
        "vm": vm,                             # Name of the VM
        "is_processing": bool(status),        # Status of the VM (0 => not available/ crashed; 1 => available)
        "uniqueid": uniqueid,                 # A unique id for each player
    }
    """

    def __init__(
        self,
        datetime: str,
        cpu: float,
        memory: float,
        vm: str,
        is_processing: bool,
        uniqueid: str,
    ):
        self.datetime = datetime
        self.cpu = cpu
        self.memory = memory
        self.vm = vm
        self.is_processing = is_processing
        self.uniqueid = uniqueid

    @staticmethod
    def from_dict(source):
        game = GameHealthcheck(
            source["datetime"],
            source["cpu"],
            source["memory"],
            source["vm"],
            source["is_processing"],
            source["uniqueid"],
        )
        return game

    def to_dict(self) -> dict[str, Union[str, float, bool]]:
        game = {
            "datetime": self.datetime,
            "cpu": self.cpu,
            "memory": self.memory,
            "vm": self.vm,
            "is_processing": self.is_processing,
            "uniqueid": self.uniqueid,
        }
        return game

    def __repr__(self) -> str:
        return f"GameHealthcheck(\
                datetime={self.datetime}, \
                cpu={self.cpu}, \
                memory={self.memory}, \
                vm={self.vm}\
                is_processing={self.is_processing}\
                uniqueid={self.uniqueid}\
            )"

    def json_dumps(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")
