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
"""
Warehouse VM - Flask App

Author: SampathM@google.com

Description: This is a simple flask back-end application to receive message sent
by user VM.

Web Server Features:
1. Receives all REST API calls (get/post) at `/message`
2. At `/health` provides health-check status
3. At `/load` provides os load status
4. At `/crash` provide time before crashing
5. At `/crash/now`, crashes(i.e.) pauses the processing work

"""
import datetime
import logging
import time

from lib import config
from lib.app_cache import WarehouseCache
from lib.base_app import app, APP_URLS, create_index_page
from lib.celery_task import delayed_generate_controlled_load
from lib.job_reporter import JobReporter

# Settings
HOSTNAME = config.HOSTNAME
FILE = __file__
APP_URLS += """
/process
/crash
/crash/status
/crash/now
/score
/reset
""".strip().splitlines()

# crash settings
CRASH_TIME_DURATION = 5.0  # seconds
MESSAGE_PROCESS_DURATION = 0.02  # seconds
CRASH_TIME = -1 * CRASH_TIME_DURATION

WH_APP_CACHE = WarehouseCache()
WH_APP_CACHE.reset_score_counter()
WH_APP_CACHE.set_crash_start_time()

JOB_REPORTER = JobReporter()
# WH_APP_CACHE.reset()


@app.route("/")
def warehouse_index_page():
    return create_index_page(HOSTNAME, FILE, APP_URLS)


def crash_checker(function):
    def inner_function(*args, **kwargs):
        if CRASH_TIME < time.perf_counter():
            return function(*args, **kwargs)
        else:
            # return f"System Crashed, Wait {CRASH_TIME - time.perf_counter()}"
            #  https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
            #  429: Too many requests
            # return abort(429)
            return {
                "status": "not ok!",
                "message": "request blocker is enabled! please wait",
            }

    return inner_function


@app.route("/process")
@crash_checker
def send_message() -> dict:
    # WH_APP_CACHE.incr_score_counter()
    # time.sleep(MESSAGE_PROCESS_DURATION)
    #
    # send run the job request to background queue
    response = delayed_generate_controlled_load.delay(
        duration_ms=800,
        cpu_percent=2,
        memory_percent=2,
        start_time_lag_ms=0,
        end_time_lag_ms=0,
    )
    # report a job
    queue_size = JOB_REPORTER.get_job_queue_size()

    if queue_size > config.GAME_WH_JOB_LIMIT:
        return {
            "status": "not ok",
            "hostname": HOSTNAME,
            "description": f"Queue size limit reached {queue_size}, limit is {config.GAME_WH_JOB_LIMIT}",
        }

    # register a new task
    JOB_REPORTER.register_new_task()
    #
    logging.debug(f"delayed job response {response}")
    return {
        "status": "ok",
        "total-score": WH_APP_CACHE.get_score_counter(),
        "hostname": HOSTNAME,
    }


@app.route("/score")
def process_score() -> dict:
    return {"score": WH_APP_CACHE.get_score_counter(), "hostname": HOSTNAME}


@app.route("/reset")
def reset_warehouse_stats() -> dict:
    logging.warning("Reset JobReporter")
    response1 = JobReporter().reset()
    logging.warning("Reset Warehouse App Cache")
    response2 = WH_APP_CACHE.reset()
    response = {**response1, **response2}
    response["hostname"] = HOSTNAME
    response["status"] = "ok"
    return response


@app.route("/crash/now")
def crash_scene_simulator() -> dict:
    global CRASH_TIME
    global CRASH_TIME_DURATION
    if CRASH_TIME < time.perf_counter():
        CRASH_TIME = time.perf_counter() + CRASH_TIME_DURATION
        logging.warning(f"updates CRASH_TIME to {CRASH_TIME}")
        message = {
            "start-crash-simulation": "ok",
            "time-now": datetime.datetime.now(),
            "crash-recovery-duration(sec)": CRASH_TIME_DURATION,
        }
    else:
        message = {
            "start-crash-simulation": "not ok!",
            "crash-recover-start-time(local)": CRASH_TIME,
            "crash-recover-duration(secs)": CRASH_TIME_DURATION,
            "crash-recover-wait-time(secs)": CRASH_TIME - time.perf_counter(),
            "time-now": datetime.datetime.now(),
        }
    return message


@app.route("/crash")
@app.route("/crash/status")
def crash_scene_test() -> dict:
    global CRASH_TIME
    if CRASH_TIME < time.perf_counter():
        message = {"status": "ok!"}
    else:
        message = {
            "status": "ok!",
            "recovery-wait(seconds)": CRASH_TIME - time.perf_counter(),
        }
    # return make_response(jsonify(message), 200)
    return message


def is_port_free(port) -> bool:
    """Checks if a port is available for use.
    Args: port (int): The port number to check.
    Returns: bool: True if the port is free, False otherwise.

    Note: Written by Gemini
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", int(port)))
            return True
        except OSError:
            return False


def get_free_port() -> int:
    """To find an unused port to dev port to run"""
    logging.info(f"Check free ports")
    all_port = "8000 8080 8081 8082 8083 8084 8085".split()

    for app_port in all_port:
        if is_port_free(app_port):
            logging.warning(f"using port {app_port}")
            print(f"using port {app_port}")
            return app_port
        else:
            logging.info(f"Failing  with port: {app_port}")
    raise Exception("Failed to find a valid port!")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        filemode="w",
        level=logging.DEBUG,
    )
    app.run(debug=True, port=get_free_port())
