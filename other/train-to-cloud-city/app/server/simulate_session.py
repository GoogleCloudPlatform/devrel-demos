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

import logging
import time
from train_types import *
from google.cloud import firestore
from fastapi.encoders import jsonable_encoder

PROJECT = "train-to-cloud-city-4"
STEP_SEC = 5


logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
log = logging.info

def sleep(duration):
    log(f"sleeping for {duration} seconds")
    time.sleep(duration)

def change(doc, data):
    log(f'{data}')
    doc.update(data)

# ----

world = WorldState(
    train=Train(
        actual_location=LOCATION["STATION"],
        target_location=LOCATION["STATION"],
        actual_cargo=list(),
    ),
    signals={s.slug: s for s in SIGNALS},
    pattern_slug="medium_complexity",
    proposal=None,
    proposal_result=None,
)

log("connecting to DB")
db = firestore.Client(project=PROJECT)
global_ref = db.collection("global_simulation")

while True:
    log("set starting world state")
    global_ref.document("world").set(jsonable_encoder(world))

    # print(json.dumps(jsonable_encoder(world), indent=4))

    world_ref = global_ref.document("world")

    sleep(STEP_SEC)
    change(world_ref, {"train.actual_cargo" : "['compute-engine']"})

    sleep(STEP_SEC)
    change(world_ref, {"train.actual_cargo" : "['compute-engine', 'cloud-storage']"})

    sleep(STEP_SEC)
    change(world_ref, {"signals.one.target_state" : "clear"})
    sleep(STEP_SEC / 2)
    change(world_ref, {"signals.one.actual_state" : "clear"})

    sleep(STEP_SEC)
    change(world_ref, {"signals.two.target_state" : "clear"})
    sleep(STEP_SEC / 2)
    change(world_ref, {"signals.two.actual_state" : "clear"})

    sleep(STEP_SEC)
    change(world_ref, {"signals.three.target_state" : "clear"})
    sleep(STEP_SEC / 2)
    change(world_ref, {"signals.three.actual_state" : "clear"})

    sleep(STEP_SEC)
    change(world_ref, {"signals.four.target_state" : "clear"})
    sleep(STEP_SEC / 2)
    change(world_ref, {"signals.four.actual_state" : "clear"})

    sleep(STEP_SEC)
    change(world_ref, {"train.target_location" : "one"})
    sleep(STEP_SEC)
    change(world_ref, {"train.target_location" : "two", "train.actual_location" : "one"})
    sleep(STEP_SEC)
    change(world_ref, {"train.target_location" : "three", "train.actual_location" : "two"})
    sleep(STEP_SEC)
    change(world_ref, {"train.target_location" : "four", "train.actual_location" : "three"})
    sleep(STEP_SEC)
    change(world_ref, {"train.target_location" : "station", "train.actual_location" : "four"})
    sleep(STEP_SEC)
    change(world_ref, {"train.actual_location" : "station"})

    sleep(20)

