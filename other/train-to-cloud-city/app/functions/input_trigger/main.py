# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from cloudevents.http import CloudEvent
import functions_framework
from google.cloud import firestore
from google.events.cloud import firestore as firestoredata

client = firestore.Client()

# Converts strings added to /messages/{pushId}/original to uppercase
@functions_framework.cloud_event
def input_trigger(cloud_event: CloudEvent) -> None:
    # print(cloud_event)
    firestore_payload = firestoredata.DocumentEventData()
    firestore_payload._pb.ParseFromString(cloud_event.data)
    # print(firestoredata.DocumentEventData.to_json(firestore_payload))


    # extract the actual data from protobuf nonsense
    print("\nOld value:")
    old_input = firestore_payload.old_value.fields["input"].string_value
    print(old_input)

    print("\nNew value:")
    new_input = firestore_payload.value.fields["input"].string_value
    print(new_input)
    
    if old_input == new_input:
        print("No change in mailbox, exiting")
        return

    path_parts = firestore_payload.value.name.split("/")
    separator_idx = path_parts.index("documents")
    collection_path = path_parts[separator_idx + 1]
    
    print(f"Collection path: {collection_path}")
    global_ref = client.collection(collection_path)

    # We've retrieved the input, clear the mailbox. 
    # The command could potentially fail, we're not going to retry.
    global_ref.document("input_mailbox").update({"input" : None})

    match new_input:
        case None | "":
            print("Input was None or empty string, exiting")
        case "reset":
            reset(global_ref, collection_path)
        case "check_pattern":
            check_pattern(global_ref, collection_path)
        case _:
            print(f"Input command not supported: {repr(new_input)}")
    return

def check_pattern(global_ref, collection_path):
    print(f"check_pattern({collection_path}")

    global_ref.document("train_mailbox").update({"input" : "do_check_cargo"})
    return 

def reset(global_ref, collection_path):
    print(f"reset({collection_path}")

    global_ref.document("train_mailbox").update({"input" : None})
    global_ref.document("input_mailbox").update({"input" : None})

    proposal_doc = global_ref.document("proposal")
    proposal_doc.update({"pattern_slug":None, "proposal_result":None})

    global_ref.document("cargo").update({"actual_cargo": []})

    signals_doc = global_ref.document("signals")

    # In Firestore, nested updates must use "dot notation": 
    # "If you update a nested field without dot notation, 
    # you will overwrite the entire map field"
    # https://cloud.google.com/firestore/docs/manage-data/add-data#update_fields_in_nested_objects
    signals_doc.update({"one.target_state" : "off"})
    signals_doc.update({"two.target_state" : "off"})
    signals_doc.update({"three.target_state" : "off"})
    signals_doc.update({"four.target_state" : "off"})
    return







