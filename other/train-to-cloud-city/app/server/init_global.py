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
import train_types
from google.cloud import firestore

PROJECT = "train-to-cloud-city-4"
COLLECTION = "global_simulation"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.info

train = train_types.Train(
    actual_location=train_types.LOCATION["STATION"],
)
cargo = train_types.Cargo(actual_cargo=list())
signals = {s.slug: s.model_dump(mode="json") for s in train_types.SIGNALS}


log("connecting to DB")
db = firestore.Client(project=PROJECT)
global_ref = db.collection(COLLECTION)

log("set starting global state")

global_ref.document("train_mailbox").set(
    {"input": None, "doc_valid_commands": ["do_check_cargo", "do_victory_lap"]}
)
global_ref.document("input_mailbox").set(
    {"input": None, "doc_valid_commands": ["reset", "check_pattern"]}
)

proposal_doc = global_ref.document("proposal")
proposal_doc.set({"pattern_slug": None, "proposal_result": None})

cargo_doc = global_ref.document("cargo")
cargo_doc.set(cargo.model_dump(mode="json"))

train_doc = global_ref.document("train")
train_doc.set(train.model_dump(mode="json"))

signals_doc = global_ref.document("signals")
signals_doc.set(signals)
