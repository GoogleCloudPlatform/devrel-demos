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

import psutil


def generate_controlled_load(
    duration_ms=300,
    cpu_percent=2,
    memory_percent=2,
    start_time_lag_ms=0,
    end_time_lag_ms=0,
):
    """
    Generates a controlled CPU and memory load for a specified duration.

    Args:
        duration_ms: The duration of the load test in milliseconds.
        cpu_percent: The target CPU loads as a percentage (0-100).
        memory_percent: The target memory load as a percentage (0-100).

    Note: Original code is written by Duet AI(Gemini), later re-factored!
    """
    # Add time lag
    if start_time_lag_ms:
        time.sleep(start_time_lag_ms)

    # Calculate start and end times
    start_time = time.time()
    end_time = start_time + duration_ms / 1000

    # Memory load generation
    mem = psutil.virtual_memory()
    target_mem_usage = mem.total * memory_percent / 100
    data = "x" * int(target_mem_usage)  # Create a data block

    # CPU load generation
    while time.time() < end_time:
        pid = os.getpid()
        py = psutil.Process(pid)
        # Try to limit to a single core for consistent measurement
        if hasattr(py, "cpu_affinity"):
            py.cpu_affinity([0])
        start = time.time()
        while time.time() - start < cpu_percent / 100:
            pass  # Busy loop to consume CPU

    # Release the memory
    del data

    # Add time lag before closing
    if end_time_lag_ms:
        time.sleep(end_time_lag_ms)


if __name__ == "__main__":
    # generate_controlled_load(duration_ms=2000, cpu_percent=5, memory_percent=10)
    import multiprocessing as mp

    def monitor(target):
        worker_process = mp.Process(target=target)
        worker_process.start()
        p = psutil.Process(worker_process.pid)

        # log cpu usage of `worker_process` every 10 ms
        cpu_percents = []
        while worker_process.is_alive():
            cpu_percents.append(p.cpu_percent())
            time.sleep(0.01)

        worker_process.join()
        return cpu_percents

    cpu_percents = monitor(target=generate_controlled_load)
    print(cpu_percents)
