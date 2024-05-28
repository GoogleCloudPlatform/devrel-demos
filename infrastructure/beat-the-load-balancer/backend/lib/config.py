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

import os
import time

GAME_VERSION = "Thu Mar 28 11:47:02 CET 2024"
GAME_APP_START_TIME = time.time()
HOSTNAME = os.uname().nodename
IS_RUNNING_IN_LOCAL = not HOSTNAME.startswith("vm-")

PROJECT_ID = "beat-the-load-balancer"
PROJECT_LOCATION = "us-central1-a"

# player worker vms
WH_VM_NAMES = [
    "vm-wh01",
    "vm-wh02",
    "vm-wh03",
    "vm-wh04",
]

# load balancer worker vms
LB_WH_VM_NAME = [
    "vm-wh91",
    "vm-wh92",
    "vm-wh93",
    "vm-wh94",
]

ALL_VM_NAMES = (
    [
        "vm-loader2",
        "vm-loader",
        "vm-main",
    ]
    + WH_VM_NAMES
    + LB_WH_VM_NAME
)

VM_IPS = {
    key: f"{key}.{PROJECT_LOCATION}.c.{PROJECT_ID}.internal" for key in ALL_VM_NAMES
}

VM_APP_PORTS = {key: "8000" for key in ALL_VM_NAMES}

# Redis Server config
if IS_RUNNING_IN_LOCAL:
    REDIS_IP_ADDRESS = "0.0.0.0"
else:
    REDIS_IP_ADDRESS = "10.10.10.1010"

REDIS_PORT_ADDRESS = "6379"

GAME_WORKER_JOB_SCORE = 1

# Time limit for celery jobs sent
GAME_COMPLETION_TIME_LIMIT = 60 * 10

GAME_WH_JOB_LIMIT = 110

GAME_LOADER_CONFIG = [
    # {"duration": 10, "users": 50, "spawn_rate": 10},
    # {"duration": 25, "users": 100, "spawn_rate": 10},
    # {"duration": 50, "users": 150, "spawn_rate": 10},
    # {"duration": 100, "users": 250, "spawn_rate": 10},
    {"duration": 1000, "users": 130, "spawn_rate": 10},
]

# Loader config
GAME_LOADER_TARGET_HOST = None
if HOSTNAME == "vm-loader":
    # Player `main` host
    GAME_LOADER_TARGET_HOST = (
        f"http://{HOSTNAME}.{PROJECT_LOCATION}.c.{PROJECT_ID}.internal:8000"
    )
elif HOSTNAME == "vm-loader2":
    # GLB static IP
    GAME_LOADER_TARGET_HOST = "http://10.10.10.1000:8000"
