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

from locust import HttpUser, task, between
from locust import LoadTestShape
from locust.log import setup_logging

import config

HOSTNAME = os.uname().nodename
logging.basicConfig(level=logging.DEBUG)
setup_logging("INFO", None)


class SharpStepShape(LoadTestShape):
    stages = config.GAME_LOADER_CONFIG

    def tick(self):
        run_time = self.get_run_time()

        if run_time >= 60:
            self.runner.quit()

        # default
        default_users_count = 10
        default_spawn_rate = 5

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        return default_users_count, default_spawn_rate


class WarehouseVM(HttpUser):
    host = config.GAME_LOADER_TARGET_HOST
    if host is None or not host.endswith("8000"):
        _error_msg = "No IP is configured for the Locust! Please check"
        logging.warning(_error_msg)
        raise Exception(_error_msg)

    wait_time = between(1, 5)

    @task
    def process_requests(self):
        self.client.get("/process")

    def on_start(self):
        logging.warning("Starting locust\n" * 3)

    def on_stop(self):
        logging.warning("Stopping locust\n" * 3)
