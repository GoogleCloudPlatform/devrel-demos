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

import json
from typing import Union


class GameScore:
    """
    message = {
        "datetime": _datetime,          # Time-stamp denoting the message creation time at VM (UTC)
        "player_type": ["human", "load_balancer"] # Identifies the player type for this score message
        "score": str(score),            # Score to be awarded for message processing
        "vm": vm,                       # Name of the VM. Indicates where the message was processed
        "difficulty": str(difficulty),  # Current game difficulty level
        "uniqueid": uniqueid,           # A unique id for each player
    }
    """

    def __init__(
        self,
        datetime: str,
        player_type: str,
        score: int,
        vm: str,
        difficulty: int,
        uniqueid: str,
    ):
        self.datetime = datetime
        self.player_type = player_type
        self.score = score
        self.vm = vm
        self.difficulty = difficulty
        self.uniqueid = uniqueid

    @staticmethod
    def from_dict(source):
        game = GameScore(
            source["datetime"],
            source["player_type"],
            source["score"],
            source["vm"],
            source["difficulty"],
            source["uniqueid"],
        )
        return game

    def to_dict(self) -> dict[str, Union[str, int]]:
        game = {
            "datetime": self.datetime,
            "player_type": self.player_type,
            "score": self.score,
            "vm": self.vm,
            "difficulty": self.difficulty,
            "uniqueid": self.uniqueid,
        }
        return game

    def __repr__(self) -> str:
        return f"GameScore(\
                datetime={self.datetime}, \
                player_type={self.player_type}, \
                score={self.score}, \
                vm={self.vm}, \
                difficulty={self.difficulty}\
                uniqueid={self.uniqueid}\
            )"

    def json_dumps(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")
