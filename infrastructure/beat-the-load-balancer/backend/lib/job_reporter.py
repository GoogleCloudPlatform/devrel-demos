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

import redis

from lib import config

redis_client = redis.StrictRedis(config.REDIS_IP_ADDRESS, port="6379")


class JobReporter:

    def __init__(self):
        self.redis_client = redis_client

        self.vm_registered_tasks = 0
        self.vm_registered_tasks_key = f"{config.HOSTNAME}-tasks-registered"

        self.vm_completed_tasks = 0
        self.vm_completed_tasks_key = f"{config.HOSTNAME}-tasks-completed"

    def reset(self) -> dict:
        # clear any running jobs
        # self.clean_up_pending_active_jobs()
        self.vm_registered_tasks = 0
        self.vm_completed_tasks = 0

        self.redis_client.set(self.vm_registered_tasks_key, self.vm_registered_tasks)
        self.redis_client.set(self.vm_completed_tasks_key, self.vm_completed_tasks)

        response = dict(
            {
                self.vm_registered_tasks_key: self.vm_registered_tasks,
                self.vm_completed_tasks_key: self.vm_completed_tasks,
            }
        )
        logging.warning("---")
        logging.warning(response)
        return response

    def register_new_task(self):
        self.redis_client.incr(self.vm_registered_tasks_key)

    def register_completed_task(self):
        self.redis_client.incr(self.vm_completed_tasks_key)

    def job_queue_status(self):
        registered = self.redis_client.get(self.vm_registered_tasks_key)
        completed = self.redis_client.get(self.vm_completed_tasks_key)
        return {
            "HOSTNAME": config.HOSTNAME,
            "REGISTERED": registered,
            "COMPLETED": completed,
        }

    def get_job_queue_size(self):
        registered = self.redis_client.get(self.vm_registered_tasks_key)
        completed = self.redis_client.get(self.vm_completed_tasks_key)
        return int(registered) - int(completed)
