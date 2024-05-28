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

import psutil
import redis

from lib import config
from lib.profiler import execution_timer
from lib.pubsub import send_system_health_message

hostname = config.HOSTNAME
redis_client = redis.StrictRedis(config.REDIS_IP_ADDRESS, port=config.REDIS_IP_ADDRESS)


class SystemLoad:

    def __init__(self):
        self.cpu_load = None
        self.mem_load = None
        self.interval_time = 0.5  # 500 milli-seconds
        self.cpu_load_key = f"{config.HOSTNAME}_load_cpu_500ms"
        self.mem_load_key = f"{config.HOSTNAME}_load_mem_500ms"
        self.player_name_key = "game_player_name"

    def __repr__(self):
        return f"SystemLoad(cpu: {self.cpu_load}, mem: {self.mem_load})"

    def _update_system_health(self, cpu_load, mem_load):
        self.cpu_load = cpu_load
        self.mem_load = mem_load

    def update_system_health_to_redis(self, cpu_load=None, mem_load=None):
        # if provided, update the cpu_load info
        if cpu_load or mem_load:
            self._update_system_health(cpu_load, mem_load)
        # update info to redis
        redis_client.set(self.cpu_load_key, self.cpu_load)
        redis_client.set(self.mem_load_key, self.mem_load)
        logging.info("SystemLoad: Upload from Redis")

    def update_system_health_to_pubsub(self):
        user_name = redis_client.get(self.player_name_key).decode("utf")
        send_system_health_message(
            cpu=self.cpu_load,
            memory=self.mem_load,
            vm=config.HOSTNAME,
            uniqueid=user_name,
        )

    def get_os_system_health(self, time_interval=None):
        logging.info("SystemLoad: Read from OS")
        fist_cpu_load = psutil.cpu_percent()
        if time_interval:
            self.cpu_load = psutil.cpu_percent(interval=time_interval)
        self._update_system_health(
            psutil.cpu_percent(time_interval), psutil.virtual_memory().percent
        )
        return fist_cpu_load, self.cpu_load, self.mem_load

    def get_system_health_from_redis(self):
        logging.info("SystemLoad: Read from Redis")
        self._update_system_health(
            redis_client.get(self.cpu_load_key).decode("utf"),
            redis_client.get(self.mem_load_key).decode("utf"),
        )

    def get_system_health(self, live_data=True):
        if live_data:
            self.get_os_system_health()

        # update info to redis
        self.update_system_health_to_redis()
        return dict(
            {
                "CPU": self.cpu_load,
                "MEMORY": self.mem_load,
                "HOSTNAME": hostname,
            }
        )


@execution_timer
def get_system_health():
    cpu = psutil.cpu_percent()
    response = dict(
        {
            "CPU": cpu,
            "MEMORY": psutil.virtual_memory().percent,
            "HOSTNAME": hostname,
            "_IS_LIVE": "true",
        }
    )
    for i in range(3):
        response[f"CPU-{round(0.200 * (i + 1), 1)}(ms)"] = psutil.cpu_percent(0.200 * i)
    return response
