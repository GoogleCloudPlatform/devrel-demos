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
import random
import time

from lib.base_app import app, create_index_page, APP_URLS
from lib.celery_task import run_os_command

# Settings
HOSTNAME = os.uname().nodename
APP_URLS += """
/load/start
/send-messages
""".strip().splitlines()


@app.route("/")
def warehouse_index_page():
    return create_index_page(HOSTNAME, __file__, APP_URLS)


@app.route("/reset")
def reset_loader():
    return {"status": "ok", "message": "nothing to reset"}


def is_locust_running(flag_file) -> bool:
    """Runs locust load generator while ensuring that, it runs at most once
    every 60 seconds. Uses a flag tile to store that time of the last execution.
    """
    try:
        logging.debug("- checking temporary file!")
        with open(flag_file, "r") as f:
            timestamp = float(f.read())
            return time.time() - timestamp <= 60
    except FileNotFoundError:
        logging.debug("- found no temporary file!")
        return False


def get_locust_command():
    unique_id = "".join(random.sample("abcdefghijklmnopqrstuvwxyz", 4))
    log_file = f"/tmp/flask-loader-logs-{unique_id}.log"
    command = [
        "/home/sampathm/load-balancing-blitz/venv/bin/locust",
        "--headless",
        "-t 60s",
        "-f",
        "/home/sampathm/load-balancing-blitz/app/lib/locustfile.py",
        # "--logfile",
        # str(locust_run_report),
    ]
    command = " ".join(command)
    logging.debug(f"- command for Locust! {command}")
    return command


@app.route("/load/start")
@app.route("/send-messages")
def main():
    os_command = get_locust_command()
    logging.debug(f"Trigger Running Locust! {run_os_command.delay(os_command)}")
    return {"start-messages": "ok"}


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        filemode="w",
        level=logging.DEBUG,
    )
    app.run(debug=True, port="8000")
