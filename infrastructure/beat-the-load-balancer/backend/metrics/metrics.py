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
import logging

# common config
from lib.config import HOSTNAME, WH_VM_NAMES, LB_WH_VM_NAME
from lib.profiler import execution_timer
from metrics import game_healthcheck, game_record, game_score
from metrics.pubsub import (
    send_healthcheck_to_pubsub,
    send_score_to_pubsub,
    send_game_record_to_pubsub,
)


@execution_timer
def send_system_health_message(cpu, memory, vm, status, uniqueid) -> None:
    _datetime = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    # Create the healthcheck object
    healthcheck_message = game_healthcheck.GameHealthcheck(
        _datetime, cpu, memory, vm, bool(status), uniqueid
    )
    logging.debug(f"Healthcheck message: {healthcheck_message.__str__()}")
    result = send_healthcheck_to_pubsub(healthcheck_message.json_dumps())
    logging.info(f"Published healthcheck message ID: {result}")


@execution_timer
def send_score_message(score, vm, uniqueid, difficulty) -> None:
    _datetime = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    # Get the current player type from "lib.config"
    if HOSTNAME in WH_VM_NAMES:
        player_type = "human"
    elif HOSTNAME in LB_WH_VM_NAME:
        player_type = "load_balancer"
    else:
        # Ignore the message if it doesn't correspond to either of the player types.
        return

    # Create the score object
    score_message = game_score.GameScore(
        _datetime, player_type, score, vm, difficulty, uniqueid
    )
    logging.debug(f"Score message: {score_message.__str__()}")
    result = send_score_to_pubsub(score_message.json_dumps())
    logging.info(f"Published score message ID: {result}")


@execution_timer
def send_game_record_message(game_record_type, uniqueid) -> None:
    assert game_record_type in "start stop genai".split()
    _datetime = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    game_record_message = game_record.GameRecord(_datetime, game_record_type, uniqueid)
    logging.debug(f"Game record message: {game_record_message.__str__()}")
    result = send_game_record_to_pubsub(game_record_message.json_dumps())
    logging.info(f"Published game record message ID: {result}")
