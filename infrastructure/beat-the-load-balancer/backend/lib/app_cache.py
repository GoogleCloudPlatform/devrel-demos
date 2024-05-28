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
import time

import lib.job_reporter
from lib import base_cache
from lib import config


class GameCacheVariables(base_cache.RedisHelper):
    """
    Class for all Game related cached related variable's (redis) keys names
     and their default values.
    """

    def __init__(self):
        super().__init__()

        self.wh_vms = config.WH_VM_NAMES
        self.lb_wh_vms = config.LB_WH_VM_NAME
        self.all_wh_vms = self.wh_vms + self.lb_wh_vms

        # Warehouse variables - keys & default values
        self.score_counter_key_default = 0
        self.score_counter_key = f"{config.HOSTNAME}_score".lower()

        self.crash_start_time = str(datetime.datetime.now())
        self.crash_start_time_key = f"{config.HOSTNAME}_crash_start_time".lower()

        self.crash_start_time_key_counter = 0
        self.crash_start_time_key_counter_key = (
            f"{config.HOSTNAME}_crashes_count".lower()
        )

        # Player
        self.player_name = "-no-name-"
        self._default_player_name = "-no-name-"
        self.player_name_key = "game_player_name"

        self.game_start_time_key = "game_start_time"
        self.game_start_time_key_default_value = "0.0"  # str(time.time() - 60)

        self.player_task_score = config.GAME_WORKER_JOB_SCORE
        self.player_task_score_key = "game_task_score"

        self.selection_mgr = base_cache.RedisSelectionManager()
        self.player_selected_vm_key = self.selection_mgr.selected_vm_key
        self.player_selected_vm_counter_key = self.selection_mgr.selected_vm_counter_key

        # Warehouse & Player stats
        self.all_vms_crash_counts = self.all_vms_ip_keys = [
            f"{_hostname}_crashes_count".lower() for _hostname in self.all_wh_vms
        ]

        self.all_vms_ip_keys = [
            f"{_hostname}_IP".lower() for _hostname in self.all_wh_vms
        ]
        self.all_vms_ip_internal_keys = [
            f"{_hostname}_internal_ip".lower() for _hostname in self.all_wh_vms
        ]

        # SystemHealth
        self.all_vms_cpu_keys = [
            f"{_hostname}_load_cpu_500ms".lower() for _hostname in self.all_wh_vms
        ]
        self.all_vms_mem_keys = [
            f"{_hostname}_load_mem_500ms".lower() for _hostname in self.all_wh_vms
        ]

        self.all_vms_score_keys = [
            f"{_hostname}_score".lower() for _hostname in self.all_wh_vms
        ]
        self.all_celery_request_task_keys = [
            f"{_hostname}-tasks-registered".lower() for _hostname in self.all_wh_vms
        ]
        self.all_celery_completed_task_keys = [
            f"{_hostname}-tasks-completed".lower() for _hostname in self.all_wh_vms
        ]

    def is_game_in_progress(self) -> bool:
        game_start_time = float(self.get(self.game_start_time_key))
        time_diff = time.time() - game_start_time
        return time_diff <= config.GAME_COMPLETION_TIME_LIMIT


class PlayerCache(GameCacheVariables):

    def reset(self):
        """Reset player game cache"""

        # safety check
        # if self.is_game_in_progress():
        #     return self.reset_during_game_in_progress()

        # reset player name
        self.player_name = self._default_player_name
        self.set(self.player_name_key, self.player_name)

        # rest game start time
        self.set(self.game_start_time_key, self.game_start_time_key_default_value)

        # reset player score
        self.player_task_score = 10
        self.set(self.player_task_score_key, self.player_task_score)

        response1 = dict(
            {
                self.player_task_score_key: self.player_task_score,
                self.player_name_key: self.player_name,
            }
        )
        # response2 = base_cache.RedisSelectionManager(config.WH_VM_NAMES).reset()
        response2 = self.selection_mgr.reset()

        response = {**response1, **response2}

        logging.warning("---")
        logging.warning(response)
        return response

    def reset_player_name(self):
        self.player_name = self._default_player_name
        self.set(self.player_name_key, self.player_name)

    def start_the_game(self, player_name):
        self.player_name = player_name
        self.set(self.player_name_key, player_name)

        # update game time flag
        self.set(self.game_start_time_key, str(time.time()))

    def stop_the_game(self):
        self.set(self.game_start_time_key, self.game_start_time_key_default_value)

    def get_player_name(self):
        return self.get(self.player_name_key)

    # def set_task_score(self, score=10):
    #     self.player_task_score = score
    #     self.set(self.player_task_score_key, self.player_task_score)

    def _prepare_dict_(self, keys, redis_value_keys):
        values = self.mget(redis_value_keys)
        return dict(zip(keys, values))

    def get_vm_all_ips(self):
        keys = self.all_wh_vms
        values_keys = self.all_vms_ip_internal_keys
        return self._prepare_dict_(keys, values_keys)

    def get_vm_all_scores(self):
        keys = self.all_wh_vms
        values_keys = self.all_vms_score_keys
        return self._prepare_dict_(keys, values_keys)

    def get_all_vm_health_stats(self):
        keys = self.all_wh_vms
        cpu_values = self.mget(self.all_vms_cpu_keys)
        mem_values = self.mget(self.all_vms_mem_keys)
        tasks_reported = self.mget(self.all_celery_request_task_keys)
        tasks_completed = self.mget(self.all_celery_completed_task_keys)

        response = list()
        for x, y, z, p, q in zip(
            keys, cpu_values, mem_values, tasks_reported, tasks_completed
        ):
            response.append(
                dict(
                    {
                        "HOSTNAME": x,
                        "CPU": y,
                        "MEMORY": z,
                        "TASK_REGISTERED": p,
                        "TASK_COMPLETED": q,
                        "QUEUE": int(p) - int(q),
                    }
                )
            )
        return response

    def get_all_vm_stats(self):
        game_stats = dict(
            {
                "ALL_VMS": self.all_wh_vms,
                "ALL_SCORES": self.mget(
                    self.all_vms_score_keys
                ),  # self.get_vm_all_scores(),
                "ALL_CPU": self.mget(self.all_vms_cpu_keys),
                "ALL_MEM": self.mget(self.all_vms_mem_keys),
                "ALL_TASKS_REGISTERED": self.mget(self.all_celery_request_task_keys),
                "ALL_TASKS_COMPLETED": self.mget(self.all_celery_completed_task_keys),
                "ALL_VMS_CRASHES_COUNT": self.mget(self.all_vms_crash_counts),
            }
        )

        # inner function
        def get_list_diff(items1, items2):
            return [str(int(key1) - int(key2)) for key1, key2 in zip(items1, items2)]

        game_talley = dict(
            {
                "QUEUE": get_list_diff(
                    game_stats["ALL_TASKS_REGISTERED"],
                    game_stats["ALL_TASKS_COMPLETED"],
                ),
                "GAME_VM_SELECTION_UPDATES": self.selection_mgr.get_vm_selections_count(),
                "GAME_VM_SELECTION": self.selection_mgr.get_selected_vm(),
                "GAME_PLAYER_NAME": self.get_player_name(),
                "GAME_START_TIME": self.get(self.game_start_time_key),
                "GAME_IS_IN_PROGRESS": self.is_game_in_progress(),
            }
        )
        # Add total scores
        _scores = [int(x) for x in game_stats["ALL_SCORES"]]
        game_stats["GAME_SCORE_PLAYER"] = sum(_scores[:4])
        game_stats["GAME_SCORE_GCLB"] = sum(_scores[-4:])
        game_stats["GAME_CURRENT_TIME"] = round(
            time.time() - float(game_talley["GAME_START_TIME"]), 4
        )

        # combining the stats & tally
        response = {**game_stats, **game_talley}
        return response


class WarehouseCache(GameCacheVariables):

    def __init__(self):
        super().__init__()

        self.job_reporter = lib.job_reporter.JobReporter()

    def celery_queue_status(self):
        return self.job_reporter.job_queue_status()

    def reset(self) -> dict:
        # safety check
        # if self.is_game_in_progress():
        #     return self.reset_during_game_in_progress()

        # score update
        self.score_counter = 0
        self.set(self.score_counter_key, self.score_counter)

        self.crash_start_time = str(datetime.datetime.now())
        self.set(self.crash_start_time_key, self.crash_start_time)

        self.crash_start_time_key_counter = 0
        self.set(
            self.crash_start_time_key_counter_key, self.crash_start_time_key_counter
        )
        response_dict = dict(
            {
                self.score_counter_key: self.score_counter,
                self.crash_start_time_key: self.crash_start_time,
                self.crash_start_time_key_counter_key: self.crash_start_time_key_counter,
            }
        )

        #
        # response_dict1 = self.reset_warehouse_data()
        response_dict2 = self.job_reporter.reset()

        response = {
            f"{config.HOSTNAME}-WH-RESET": response_dict,
            f"{config.HOSTNAME}-CELERY-RESET": response_dict2,
        }

        logging.warning("---")
        logging.warning(response)
        return response

    def set_crash_start_time(self):
        self.set(self.crash_start_time_key, str(datetime.datetime.now()))

    def reset_crash_start_time(self):
        self.set_crash_start_time()

    def get_crash_start_time(self):
        self.get(self.crash_start_time_key)

    def incr_crash_counter(self):
        self.incr(self.crash_start_time_key_counter_key, 1)

    # def set_score_counter(self, value=0):
    #     self.set(self.score_counter_key, value)

    def reset_score_counter(self):
        self.set(self.score_counter_key, self.score_counter_key_default)

    def get_score_counter(self) -> int:
        return self.get(self.score_counter_key)

    def incr_score_counter(self, value):
        self.incr(self.score_counter_key, value)
