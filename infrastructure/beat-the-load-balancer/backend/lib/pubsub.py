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

import datetime
import json
import logging
import os
from dataclasses import dataclass

from google.cloud import pubsub_v1

from lib import config
from lib.profiler import execution_timer

_path_prefix = __file__.rsplit(os.path.sep, 2)[0]
_file_path = ""

if not os.path.isfile(_file_path):
    raise FileNotFoundError("Expected a Json Service Account file!")

_publisher_client = pubsub_v1.PublisherClient.from_service_account_json(
    os.path.join(
        __file__.rsplit(os.path.sep, 2)[0],
        _file_path,
    )
)


@dataclass
class PubSubTopic:
    # health check - hc
    health_check = _publisher_client.topic_path(
        config.PROJECT_ID, "game_vm_health_check"
    )
    # VM Scores
    score = _publisher_client.topic_path(config.PROJECT_ID, "game_vm_score")
    # Game Events - start, stop, gemini
    events = _publisher_client.topic_path(config.PROJECT_ID, "game_events")


@execution_timer
def send_system_health_message(
    cpu=0.1, memory=0.2, vm=config.HOSTNAME, status=1, uniqueid="chilling-rabbit"
):
    # https://stackoverflow.com/questions/74413230/pubsub-bigquery-subscription-using-topic-schema-for-timestamp
    logging.info(f"PubSub: Preparing to publish message")
    _datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    message = {
        # creating a time-stamp when this message is created at VM
        #  canonical format: YYYY-[M]M-[D]D[( |T)[H]H:[M]M:[S]S[.F]]
        "datetime": _datetime,
        # cpu load
        "cpu": cpu,
        # memory load
        "memory": memory,
        # name of the VM, origin of message
        "vm": vm,
        # status on message processing (0 => not avail; 1 => avail)
        "is_processing": bool(status),
        # a random id, for _run_in_local proposes
        "uniqueid": uniqueid,
    }
    logging.debug(message)
    pubsub_message_data = json.dumps(message).encode("utf-8")
    future = _publisher_client.publish(PubSubTopic.health_check, pubsub_message_data)
    logging.info(f"PubSub: Published message ID: {future.result()}")
    return pubsub_message_data


if __name__ == "__main__":
    logging.basicConfig(
        # filename=f"/tmp/flask_app_{config.HOSTNAME}.log",
        format="%(asctime)s - %(message)s",
        filemode="w",
        level=logging.DEBUG,
    )
    send_system_health_message(1.5, 2.5)
