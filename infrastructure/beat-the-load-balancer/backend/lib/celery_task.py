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

import logging
import os

import redis
from celery import Celery

from lib import config
from lib.app_cache import PlayerCache, WarehouseCache
from lib.job_reporter import JobReporter
from lib.load import generate_controlled_load
from metrics.metrics import send_score_message

redis_client = redis.StrictRedis(config.REDIS_IP_ADDRESS, port="6379")
celery_app = Celery(
    f"{config.HOSTNAME}-tasks", broker=f"redis://{config.REDIS_IP_ADDRESS}"
)

PLAYER_APP_CACHE = PlayerCache()
WH_APP_CACHE = WarehouseCache()


@celery_app.task(queue=config.HOSTNAME)
def delayed_generate_controlled_load(*args, **kwargs):
    # logging.info("celery_task: starting the `generate_controlled_load` job")
    if PLAYER_APP_CACHE.is_game_in_progress():
        # run the task
        generate_controlled_load(*args, **kwargs)
        # report the score
        WH_APP_CACHE.incr_score_counter(value=config.GAME_WORKER_JOB_SCORE)
        player_name = PLAYER_APP_CACHE.get_player_name()
        send_score_message(
            score=config.GAME_WORKER_JOB_SCORE,
            vm=config.HOSTNAME,
            uniqueid=player_name,
            difficulty=1,
        )
        logging.info("celery_task: completed the `generate_controlled_load` job")
    else:
        logging.info("celery_task: skip the `generate_controlled_load` job")

    # report the task
    JobReporter().register_completed_task()
    return WH_APP_CACHE.get_score_counter()


@celery_app.task(queue=config.HOSTNAME)
def run_os_command(os_command):
    try:
        logging.debug(f"celery_task: Running os command {os_command}")
        os.system(os_command)

    except Exception:
        logging.exception(f"celery_task: Failed to run {os_command}")
    logging.debug(f"celery_task: Running os command {os_command}")
