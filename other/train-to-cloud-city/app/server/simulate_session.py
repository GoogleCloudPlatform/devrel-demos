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
import random
import sys
import time
import train_types
from google.cloud import firestore

PROJECT = "train-to-cloud-city-4"
COLLECTION = "global_simulation"
STEP_SEC = 5

if len(sys.argv) > 1:
    PROJECT = sys.argv[1]

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.info

def sleep(duration):
    log(f"sleeping for {duration} seconds")
    time.sleep(duration)

def change(doc, data):
    log(f'{data}')
    doc.update(data)

# ----

cargo_pool = set()
for pattern in train_types.PATTERNS.values():
    # print(pattern)
    for checkpoint in pattern.checkpoints:
        for service in checkpoint.satisfying_services:
            # print(service)
            cargo_pool.add(service)
print(f"cargo_pool: {cargo_pool}")

pattern_pool = list(train_types.PATTERNS.keys())
print(f"pattern_pool: {pattern_pool}")



log(f"connecting to DB: {COLLECTION} in {PROJECT}")
db = firestore.Client(project=PROJECT)
global_ref = db.collection(COLLECTION)

while True:
    log("set starting world state")
    
    global_ref.document("input_mailbox").update({"input" : "reset"})

    proposal_doc = global_ref.document("proposal")
    cargo_doc = global_ref.document("cargo")
    signals_doc = global_ref.document("signals")

    session_cargo = set()

    # only clear these in simulation
    signals_doc.update({"one.actual_state" : "off"})
    signals_doc.update({"two.actual_state" : "off"})
    signals_doc.update({"three.actual_state" : "off"})
    signals_doc.update({"four.actual_state" : "off"})    
 
    train_doc = global_ref.document("train")
    change(train_doc, {"actual_location" : "station"})
    change(train_doc, {"actual_state" : "at_station"})

    
    sleep(STEP_SEC)    


    log("start simulation activity")
    change(proposal_doc, {"pattern_slug":random.choice(pattern_pool)})
    
    # update cargo and signals
    for i in range(0, 4):
        # choose random cargo
        sleep(STEP_SEC)
        # add a random cargo slug which is not already in session_cargo
        session_cargo.add(random.choice(list(cargo_pool.difference(session_cargo))))
        change(cargo_doc, {"actual_cargo" : list(session_cargo)})

        # sleep then update signal based on signal.target_state? 
        sleep(STEP_SEC / 2)
        signals_state = signals_doc.get()
        if signals_state.exists:
            for key, signal in signals_state.to_dict().items():
                if signal['target_state'] != signal['actual_state']:
                    print(f'{key}: {signal}')
                    change(signals_doc, {f"{key}.actual_state" : signal['target_state']})
    
    #sleep(STEP_SEC)

    # check train_mailbox... if do_victory_lap, then ... do it
    train_mailbox = global_ref.document("train_mailbox").get()
    if train_mailbox.exists:
        print(f'train_mailbox: {train_mailbox.to_dict()}')
        if train_mailbox.to_dict().get('input', '') == 'do_victory_lap':
            change(train_doc, {"actual_state" : "victory_lap"})

            sleep(STEP_SEC)
            change(train_doc, {"actual_location" : "checkpoint_1"})
            sleep(STEP_SEC)
            change(train_doc, {"actual_location" : "checkpoint_2"})
            sleep(STEP_SEC)
            change(train_doc, {"actual_location" : "checkpoint_3"})
            sleep(STEP_SEC)
            change(train_doc, {"actual_location" : "checkpoint_4"})
            sleep(STEP_SEC)
            change(train_doc, {"actual_location" : "station"})

    sleep(20)

