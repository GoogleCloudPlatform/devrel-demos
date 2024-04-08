#!/usr/bin/python
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
from datetime import datetime
from threading import Lock

import google.cloud.bigtable.row_filters as row_filters
from flask import Flask, render_template
from flask_socketio import SocketIO
from google.cloud import bigtable

async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

DEFAULT_ID = 999999999999
RESET_ID_TIMEOUT = 30
CAR_ERR_TIMEOUT = 15

OK = 0
DONE = 1
WIN = 2
ERR = 3

COLORS = {
    OK: 0,
    DONE: 1,
    WIN: 2,
    ERR: 3,
}

project_id = os.environ["PROJECT_ID"]
instance_id = "data-dash"
table_id = "races"

client = bigtable.Client(project=project_id)
instance = client.instance(instance_id)
table = instance.table(table_id)
column_family_id = "cf"


def get_data(track_id):
    # get_track_data returns the data for the last race on a track
    data = {}
    _r = table.read_rows(
        filter_=row_filters.RowKeyRegexFilter(bytes(f"^track{track_id}#.*", "utf-8")),
        limit=1,
    )

    # Expand Bigtable read to a reusable object
    row = None
    for _ in _r:
        row = _

    data["car_id"] = row.cells["cf"][b"car_id"][0].value.decode("utf-8")
    data["timestamp"] = datetime.timestamp(row.cells["cf"][b"car_id"][0].timestamp)

    col_strf = "cp{i}"
    checkpoints = {}
    for i in range(1, 9):
        col_name = bytes(col_strf.format(i=i), "utf-8")
        col = row.cells["cf"].get(col_name)
        checkpoints[i] = float(col[0].value.decode("utf-8")) if col else None

    for i in range(1, 3):
        ts = checkpoints.get(i)
        if ts:
            if checkpoints.get(8):
                status = DONE
                break
            else:
                status = ERR if time.time() - int(ts) > CAR_ERR_TIMEOUT else OK
                break
        else:
            status = ERR

    data["checkpoints"] = checkpoints
    data["status"] = status
    return data


def background_thread():
    while True:
        socketio.sleep(1)
        left_data = get_data(1)
        right_data = get_data(2)

        # Determine if there's a winner
        if left_data["status"] == DONE and right_data["status"] == DONE:
            if left_data["checkpoints"]["8"] < right_data["checkpoints"]["8"]:
                left_data["status"] = WIN
            else:
                right_data["status"] = WIN
        elif left_data["status"] == DONE:
            left_data["status"] = WIN
        elif right_data["status"] == DONE:
            right_data["status"] = WIN
        socketio.emit("send_data", {"left": left_data, "right": right_data})


@app.route("/")
def index():
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    socketio.emit(
        "set_pictures", {"left_id": f"{DEFAULT_ID}", "right_id": f"{DEFAULT_ID}"}
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
