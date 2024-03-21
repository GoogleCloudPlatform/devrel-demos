# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Union, List, Dict, Tuple, Optional
from pydantic import BaseModel
import json
import enum

class Service(BaseModel):
    slug: str
    name: str
    description: str
    doc_url: str

class Checkpoint(BaseModel):
    slug: str
    name: str
    description: str
    # a list of Service.slug
    satisfying_services: List[str]

class Pattern(BaseModel):
    slug: str
    name: str
    description: str
    checkpoints: List[Checkpoint]

class Proposal(BaseModel):
    pattern_slug: str
    """a list of Service.slug"""
    service_slugs: List[str]

class CheckpointResult(BaseModel):
    checkpoint: Checkpoint
    blocked: bool  # change name... to something else? blocked
    reason: str

class ProposalResult(BaseModel):
    blocked: bool 
    reason: str
    pattern: Pattern
    checkpoint_results: List[CheckpointResult]

PATTERNS = {
    "always_success" : Pattern(slug="always_success",name = "Always Success", description= "Always Successful", checkpoints=list()),
    "low_complexity" : 
        Pattern(
            slug = "low_complexity",
            name  = "Low Complexity",
            description = "A fairly simple pattern.",
            checkpoints = [
                Checkpoint(
                    slug = "any_service",
                    name = "Any Service Checkpoint",
                    description = "Absolutely anything is fine",
                    satisfying_services = ["*"], # I guess "*" is magic? Ungh. 
                ),
            ],
        ),
    "medium_complexity" : 
        Pattern(
            slug =  "medium_complexity",
            name = "Medium Complexity",
            description = "A medium complexity pattern. Need to compute something.",
            checkpoints = [
                Checkpoint(
                    slug = "compute",
                    name = "Compute Checkpoint",
                    description = "We need some kind of compute.",
                    satisfying_services = ["app-engine", "cloud-functions", "cloud-run", "gke", "compute-engine"],
                ),
            ],
        ),
}

# init
with open("static/services.json") as file:
    data = json.load(file)
SERVICES = {}
for key, raw in data.items():
    service = Service(description=raw["four_words"], **raw)
    SERVICES[key] = service


# train & signals

# TODO: rethink this. Do we want to have fixed locations? Do they need ordering?
# bleh... workstations defaults to Python 3.10, which doesn't have enum.StrEnum (added in 3.11)
# not going to troubleshoot upgrading right now
# class Location(enum.StrEnum):
#     STATION: "station"
#     CHECKPOINT_ONE: "checkpoint_one"
#     CHECKPOINT_TWO: "checkpoint_two"
#     CHECKPOINT_THREE: "checkpoint_three"
#     CHECKPOINT_FOUR: "checkpoint_four"

# class SignalState(StrEnum):
#     Stop: "stop"
#     CLEAR: "clear"

LOCATION = {
    "STATION": "station",
    "ONE": "one",
    "TWO": "two",
    "THREE": "three",
    "FOUR": "four",
}

SIGNAL_STATE = {
    "STOP": "stop",
    "CLEAR": "clear",
}

class Signal(BaseModel):
    slug: str
    name: str
    actual_state: str
    target_state: str

SIGNALS = [
    Signal(slug="one", name="One", actual_state=SIGNAL_STATE["STOP"], target_state=SIGNAL_STATE["STOP"]),
    Signal(slug="two", name="Two", actual_state=SIGNAL_STATE["STOP"], target_state=SIGNAL_STATE["STOP"]),
    Signal(slug="three", name="Three", actual_state=SIGNAL_STATE["STOP"], target_state=SIGNAL_STATE["STOP"]),
    Signal(slug="four", name="Four", actual_state=SIGNAL_STATE["STOP"], target_state=SIGNAL_STATE["STOP"]),
]


class Train(BaseModel):
    actual_location: str
    target_location: str
    actual_cargo: List[str]

# world

class WorldState(BaseModel):
    train: Train
    signals: Dict[str, Signal]
    pattern_slug: str
    proposal: Optional[Proposal]
    proposal_result: Optional[ProposalResult]
