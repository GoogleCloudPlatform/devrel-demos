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
import time
from multiprocessing import Process, Queue

import psutil

from lib.system_health import SystemLoad

logging.info(f"CronJob: Running {__file__} script!")
flag_file = "/tmp/flaskapp_hc_flag_file"


def get_system_data():
    logging.debug("CronJob: running get_system_data()")
    cpu_percent = psutil.cpu_percent(interval=None)  # Instantaneous CPU usage
    cpu_load_avg = psutil.getloadavg()[0]  # 5 seconds load average
    memory_usage = psutil.virtual_memory().percent
    return cpu_percent, cpu_load_avg, memory_usage


def update_system_data(data_queue, lag=None, time_interval=5):
    time.sleep(lag)
    logging.debug(f"CronJob: lag time {lag}")
    start_time = time.time()
    sys = SystemLoad()
    if lag:
        time.sleep(lag)
    while os.path.isfile(flag_file):
        logging.debug("CronJob: running update_system_data()")
        time_diff = time.time() - start_time

        # collect sys load
        cpu_instant_load, cpu_load, mem_load = sys.get_os_system_health(time_interval)

        # report the sys load
        sys.update_system_health_to_redis(cpu_load, mem_load)
        sys.update_system_health_to_pubsub()

        data_queue.put((time_diff, cpu_instant_load, cpu_load, mem_load))
        time.sleep(5)


def main():
    if os.path.isfile(flag_file):
        logging.warning("CronJob: Found flag file! skipping executions")
        return

    with open(flag_file, "w") as fp:
        fp.write("Delete this file to stop processing!")

    logging.debug("CronJob: running main script")

    # single thread
    # data_updater = Process(target=update_system_data, args=(data_queue, 1))
    # data_updater.start()
    # multi thread
    round_trip_time_sec = 5
    time_interval = 5
    updates_per_sec = 10
    process_count = round_trip_time_sec * updates_per_sec  # ==> 50
    process_lag = (round_trip_time_sec * 1.0) / process_count  # ==> 0.100 seconds

    # starting the threads
    data_queue = Queue()
    running_jobs = []
    for i in range(process_count):
        _data_updater = Process(
            target=update_system_data, args=(data_queue, i * process_lag, time_interval)
        )
        _data_updater.start()
        running_jobs.append(_data_updater)

    while os.path.isfile(flag_file):
        if not data_queue.empty():
            time_diff, cpu_percent, cpu_load_avg, memory_usage = data_queue.get()
            print(
                "Time",
                time_diff,
                "CPU Instant:",
                cpu_percent,
                "CPU Load Avg (5s):",
                cpu_load_avg,
                "Memory:",
                memory_usage,
            )
        time.sleep(process_lag)


if __name__ == "__main__":
    logging.basicConfig(
        filename=f"/tmp/flaskapp_hc.log",
        format="%(asctime)s - %(message)s",
        filemode="w",
        level=logging.DEBUG,
    )
    main()
