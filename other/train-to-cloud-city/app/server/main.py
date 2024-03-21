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

from typing import Union, List, Dict, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

from train_types import (Service, Checkpoint, Pattern, Proposal, CheckpointResult, ProposalResult, 
    Signal, Train, WorldState,
    SERVICES, PATTERNS, LOCATION, SIGNAL_STATE, SIGNALS)

app = FastAPI()


# handlers
@app.get("/")
def read_root():
    return {"Hello": "World!"}

@app.get("/service/")
def get_services() -> Dict[str, Service]:
    return SERVICES


@app.get("/pattern/")
def get_patterns() -> Dict[str, Pattern]:
    return PATTERNS

@app.post("/proposal/")
def post_proposal(proposal: Proposal) -> ProposalResult:
    return ProposalResult(valid=True, reason= "placeholder", pattern= PATTERNS["always_success"], checkpoints = list())

@app.get("/default_world/")
def get_default_world() -> WorldState:
    return WorldState(
        train = Train(actual_location = LOCATION["STATION"], target_location = LOCATION["STATION"], actual_cargo=list()),
        signals = {s.slug: s for s in SIGNALS},
        pattern_slug = "medium_complexity",
        proposal = None,
        proposal_result = None,
    )
