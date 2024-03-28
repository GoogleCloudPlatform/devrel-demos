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

import json 

from cloudevents.http import CloudEvent
import functions_framework
from google.cloud import firestore
from google.events.cloud import firestore as firestoredata

import train_types

client = firestore.Client()

# Update session state (Firestore docs) based on changes to train cargo
# and user selected pattern. 
# This function is triggered on any change to "global*/cargo" docs. 
@functions_framework.cloud_event
def cargo_trigger(cloud_event: CloudEvent) -> None:
    # print(cloud_event)
    firestore_payload = firestoredata.DocumentEventData()
    firestore_payload._pb.ParseFromString(cloud_event.data)
    print(firestoredata.DocumentEventData.to_json(firestore_payload).replace("\n", ""))

    # extract the actual data from protobuf nonsense
    old_cargo = firestore_payload.old_value.fields["actual_cargo"].array_value
    # print(old_cargo)
    old_cargo = [item.string_value for item in old_cargo.values]
    # print(f"Old value: {repr(old_cargo)}")

    new_cargo = firestore_payload.value.fields["actual_cargo"].array_value
    # print(new_cargo)
    new_cargo = [item.string_value for item in new_cargo.values]
    print(f"cargo/actual_cargo: {repr(old_cargo)} --> {repr(new_cargo)}\n")
    
    if old_cargo == new_cargo:
        print("No change in cargo, exiting")
        return

    path_parts = firestore_payload.value.name.split("/")
    separator_idx = path_parts.index("documents")
    collection_path = path_parts[separator_idx + 1]
    document_path = "proposal"

    print(f"Collection path: {collection_path}, Document path: {document_path}\n")
    # print(f"Document path: {document_path}")

    collection = client.collection(collection_path)
    proposal_doc = collection.document(document_path)

    if old_cargo != new_cargo:
        # print("Updating proposal_result based on cargo change")
        pattern_slug = proposal_doc.get().to_dict()["pattern_slug"]
        if not pattern_slug:
            proposal_doc.update({"proposal_result" : None})
            print("No proposal/pattern_slug found, clearing proposal_result, finished.")
            return

        # TODO: Consider getting the patterns from firestore instead? 
        pattern = train_types.PATTERNS[pattern_slug]
        pr = train_types.ProposalResult(pattern = pattern, checkpoint_results=[])
        pr.validate(service_slugs=new_cargo)
        proposal_result = {"proposal_result" : pr.model_dump(mode='json')}
        print(json.dumps(proposal_result))
        proposal_doc.update(proposal_result)

        # Update signals (stop/go lights) based on pattern_result
        signaldoc = collection.document("signals")
        # Iterate over the first four checkpoints (we have exactly four signals) and
        # update each signal in order.
        for index, cp_result in enumerate(pr.checkpoint_results[:3]):
            match cp_result.clear:
                case True:
                    target_state = train_types.SIGNAL_STATE["CLEAR"]
                case _:
                    target_state = train_types.SIGNAL_STATE["STOP"]
            signal_slug = train_types.SIGNALS[index].slug
            key = f"{signal_slug}.target_state"
            signaldoc.update({key: target_state})
        
        # If all checkpoints clear, tell the train to go!
        if pr.clear:
            collection.document("train_mailbox").update({"input" : "do_victory_lap"})
    else:
        # Value is already upper-case
        # Don't perform a second write (which can trigger an infinite loop)
        print("No change in cargo, exiting")



