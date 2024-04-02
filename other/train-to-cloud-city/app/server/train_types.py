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
from pydantic import BaseModel, Field
import json


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
    complexity: str
    description: str
    checkpoints: List[Checkpoint]


class Proposal(BaseModel):
    pattern_slug: str
    """a list of Service.slug"""
    service_slugs: List[str]


class CheckpointResult(BaseModel):
    checkpoint: Checkpoint
    clear: bool = Field(default=False)
    reason: str = Field(default="default state")

    def validate(self, service_slugs: List[str]):
        self.clear = False
        if not self.checkpoint:
            self.reason = "No checkpoint set."
            return

        for service in service_slugs:
            if service in self.checkpoint.satisfying_services:
                self.clear = True
                # TODO: lookup service name from slug here
                self.reason = f"{service} satisfys this check"
                # TODO: refactor to collect all services which satisfy
                return
            else:
                self.reason = "None of the services satisfy this check"


class ProposalResult(BaseModel):
    clear: bool = Field(default=False)
    reason: str = Field(default="default state")
    pattern: Pattern
    checkpoint_results: List[CheckpointResult]

    def validate(self, service_slugs: List[str]):
        self.clear = False
        if not self.pattern:
            self.checkpoint_results = list()
            self.reason = "No pattern set."
            return
        for checkpoint in self.pattern.checkpoints:
            result = CheckpointResult(checkpoint=checkpoint)
            result.validate(service_slugs=service_slugs)
            self.checkpoint_results.append(result)
        if all(cpr.clear for cpr in self.checkpoint_results):
            self.clear = True
            self.reason = "All checkpoints satisfied!"
        else:
            self.reason = "Some checkpoints unsatisfied."


PATTERNS = {
    "pattern_a": Pattern(
        slug="pattern_a",
        complexity="low_complexity",
        name="Deploy a simple VM server",
        description="Create and deploy a simple virtual machine in Google Cloud.",
        checkpoints=[
            Checkpoint(
                slug="compute",
                name="Compute",
                description="Select a service that allows you to create and run virtual machines on Google Cloud.",
                satisfying_services=[
                    "app-engine",
                    "gke", 
                    "compute-engine"],
            ),
        ],
    ),
    "pattern_b": Pattern(
        slug="pattern_b",
        complexity="medium_complexity",
        name="Build & deploy a container image that displays database contents",
        description="Create a pattern from the Google Cloud Platform resources available that creates and deploys a container image that displays contents of a seeded database.",
        checkpoints=[
            Checkpoint(
                slug="database",
                name="Database",
                description="Choose a resource where the can container retrieve stored data to display.",
                satisfying_services=[
                    "alloydb",
                    "cloud-bigtable",
                    "cloud-firestore",
                    "cloud-memorystore",
                    "cloud-sql",
                    "cloud-sql-insights",
                    "cloud-spanner",
                ],
            ),
            Checkpoint(
                slug="compute",
                name="Compute",
                description="Select a computing resource where we will display database data.",
                satisfying_services=[
                    "app-engine",
                    "cloud-functions",
                    "cloud-run",
                    "gke",
                    "compute-engine",
                ],
            ),
            Checkpoint(
                slug="devops",
                name="Build Image",
                description="Select a resource that can create a container image",
                satisfying_services=["cloud-build"],
            ),
            Checkpoint(
                slug="devops",
                name="Store Image",
                description="Select a resource where the built container image can be stored.",
                satisfying_services=["artifact-registry"],
            ),
        ],
    ),
    "pattern_c": Pattern(
        slug="pattern_c",
        complexity="medium_complexity",
        name="Host a database backed website",
        description="Choose Google Cloud Platform services from the available blocks which could be used to host a website and database. Example: dynamic blog, ecommerce site, etc.",
        checkpoints=[
            Checkpoint(
                slug="website",
                name="Website",
                description="Some way to serve the website to the internet",
                satisfying_services=[
                    "app-engine",
                    "cloud-functions",
                    "cloud-run",
                    "gke",
                    "compute-engine",
                ],
            ),
            Checkpoint(
                slug="database",
                name="Database",
                description="Select the database that will store website data.",
                satisfying_services=[
                    "alloydb",
                    "cloud-bigtable",
                    "cloud-firestore",
                    "cloud-memorystore",
                    "cloud-sql",
                    "cloud-sql-insights",
                    "cloud-spanner",
                ],
            ),
        ],
    ),
    "pattern_d": Pattern(
        slug="pattern_d",
        complexity="high_complexity",
        name="Build a CI/CD pipeline",
        description="Create a pattern from the Google Cloud Platform resources available that sets up a basic CI/CD (continuous integration/ continuous deployment) pipeline.",
        checkpoints=[
            Checkpoint(
                slug="build_image",
                name="Build Image",
                description="Select a resource to create your build image.",
                satisfying_services=["cloud-build"],
            ),
            Checkpoint(
                slug="store_image",
                name="Store built image",
                description="Select a resource to store your built images",
                satisfying_services=["artifact-registry"],
            ),
            Checkpoint(
                slug="compute",
                name="Compute",
                description="Select a service that allows you to create and run virtual machines on Google Cloud.",
                satisfying_services=[
                    "app-engine",
                    "gke",
                    "compute-engine",
                ],
            ),
            Checkpoint(
                slug="deploy",
                name="Deploy targets",
                description="Select a resource that allows you to create a streamlined continuous delivery with multiple deploy targets (staging, canary, prod).",
                satisfying_services=["cloud-deploy"],
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
    "OFF": "off",
}


class Signal(BaseModel):
    slug: str
    name: str
    actual_state: str
    target_state: str
    doc_valid_states: List[str] = Field(
        default=[state for state in SIGNAL_STATE.values()]
    )


SIGNALS = [
    Signal(
        slug="one",
        name="One",
        actual_state=SIGNAL_STATE["OFF"],
        target_state=SIGNAL_STATE["OFF"],
    ),
    Signal(
        slug="two",
        name="Two",
        actual_state=SIGNAL_STATE["OFF"],
        target_state=SIGNAL_STATE["OFF"],
    ),
    Signal(
        slug="three",
        name="Three",
        actual_state=SIGNAL_STATE["OFF"],
        target_state=SIGNAL_STATE["OFF"],
    ),
    Signal(
        slug="four",
        name="Four",
        actual_state=SIGNAL_STATE["OFF"],
        target_state=SIGNAL_STATE["OFF"],
    ),
]


class Train(BaseModel):
    actual_location: str
    actual_state: str = Field(default="at_station")
    doc_valid_states: List[str] = Field(
        default=["at_station", "checking_cargo", "victory_lap"]
    )


class Cargo(BaseModel):
    actual_cargo: List[str]


# world


class WorldState(BaseModel):
    train: Train
    signals: Dict[str, Signal]
    pattern_slug: str
    proposal: Optional[Proposal]
    proposal_result: Optional[ProposalResult]
