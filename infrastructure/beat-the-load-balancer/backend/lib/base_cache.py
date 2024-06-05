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
import time

import redis

from lib import config
from lib import vm_selection_manager

# Global config
redis_client = redis.StrictRedis(config.REDIS_IP_ADDRESS, port="6379")


class RedisHelper:
    def __init__(self):
        logging.info(
            f"redis({self.__class__.__name__}): creating class -> ({self.__class__.__name__})"
        )
        self.redis_client = redis_client

    def incr(self, key_name, value):
        """
        Increments a key by a value.
        """
        self.redis_client.incr(key_name, value)

    def set(self, key_name, key_value):
        self.redis_client.set(key_name, key_value)
        logging.info(f"redis({self.__class__.__name__}): set {key_name} : {key_value}")

    def get(self, key_name):
        key_value = self.redis_client.get(key_name)
        return key_value.decode("utf")

    def mget(self, key_names):
        key_values = self.redis_client.mget(key_names)
        for i in range(len(key_values)):
            if key_values[i]:
                key_values[i] = key_values[i].decode("utf")
        return key_values


class RedisSelectionManager(RedisHelper, vm_selection_manager.LocalSelectionManager):
    """
    Handles VM selection and statistics.

    Uses Redis as backend memory store.
    """

    def __init__(self, vm_options=None):
        # inherit parent features
        RedisHelper.__init__(self)
        if not vm_options:
            vm_options = config.WH_VM_NAMES
        vm_selection_manager.LocalSelectionManager.__init__(self, vm_options)

        self.selected_vm = config.WH_VM_NAMES[0]
        self.selected_vm_key = "game_selected_instance"
        self.selected_vm_counter = 0
        self.selected_vm_counter_key = "game_selected_instance_counter"

        # vm expected
        self.vm_options = vm_options
        # Temp cache variables to stop VM
        self.selected_vm = None
        self.last_updated_time = 0
        # cache time limit in seconds
        self._cache_time_limit = 1
        logging.info(f"Started {__class__}")

        # cache time limit is 100 ms or 0.1 seconds
        self._cache_time_limit = 0.1

    def reset(self):
        self.selected_vm = config.WH_VM_NAMES[0]
        self.set(self.selected_vm_key, self.selected_vm)

        self.selected_vm_counter = 0
        self.set(self.selected_vm_counter_key, self.selected_vm_counter)

        response = dict(
            {
                self.selected_vm_key: self.selected_vm,
                self.selected_vm_counter_key: self.selected_vm_counter,
            }
        )

        logging.warning("---")
        logging.warning(response)
        return response

    def incr_vm_selection_count(self) -> None:
        """
        Increments the instance selection counter.
        """
        self.incr(self.selected_vm_counter_key, 1)
        logging.info(
            f"redis({self.__class__.__name__}): (Reset) Selection counter is {self.get(self.selected_vm_key)}"
        )

    def get_vm_selections_count(self):
        """
        Returns the instance selection counter.
        """
        value = self.get(self.selected_vm_counter_key)
        # logging.info(f"redis({self.__class__.__name__}): Selection Counter: {value}")
        return value

    def _read_selected_vm_from_storage(self, vm_name=None):
        """
        Reads the selected VM from storage.
        """
        # write to redis
        vm_name = self.get(self.selected_vm_key)
        # vm_name = vm_name.decode("utf-8")

        # update config
        self.selected_vm = vm_name
        self.last_updated_time = time.time()

    def _write_selected_vm_to_storage(self, vm_name):
        """
        Writes the selected VM to storage.
        """
        # write to redis
        self.set(self.selected_vm_key, vm_name)
        logging.info(
            f"redis({self.__class__.__name__}): Update VM Selection to {vm_name}"
        )
