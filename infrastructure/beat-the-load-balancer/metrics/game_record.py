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


class GameRecord:
    """
    data = {
        "datetime": _datetime,              # Time-stamp denoting the message creation time at VM (UTC)
        "game_event_type": game_event_type, # Identifies one of ["start", "stop", "genai"] events
        "uniqueid": uniqueid                # A unique id for each player
    }
    """

    def __init__(self, datetime: str, game_event_type: str, uniqueid: str):
        self.datetime = datetime
        self.game_event_type = game_event_type
        self.uniqueid = uniqueid

    @staticmethod
    def from_dict(source):
        game = GameRecord(
            source["datetime"],
            source["game_event_type"],
            source["uniqueid"],
        )
        return game

    def to_dict(self) -> dict[str, str]:
        game = {
            "datetime": self.datetime,
            "game_event_type": self.game_event_type,
            "uniqueid": self.uniqueid,
        }
        return game

    def __repr__(self) -> str:
        return f"GameRecord(\
                datetime={self.datetime}, \
                game_event_type={self.game_event_type}, \
                uniqueid={self.uniqueid}\
            )"

    def json_dumps(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")
