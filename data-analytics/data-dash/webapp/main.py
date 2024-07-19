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
import eventlet
import time
from datetime import datetime

import google.cloud.bigtable.row_filters as row_filters
from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from google.cloud import bigtable

async_mode = "eventlet"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")

DEFAULT_ID = 999999999999

OK = 0
WIN = 1
LOSE = 2
DONE = 3

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

    col_strf = "t{i}_s"
    checkpoints = {}
    for i in range(1, 9):
        col_name = bytes(col_strf.format(i=i), "utf-8")
        col = row.cells["cf"].get(col_name)
        checkpoints[str(i)] = float(col[0].value.decode("utf-8")) if col else None

    data["checkpoints"] = checkpoints
    data["status"] = DONE if checkpoints.get("8") else OK
    return data


def background_thread():
    while True:
        socketio.sleep(1)
        
        lt = time.time()
        print("GETTING LEFT DATA")
        left_data = get_data(1)
        print(f"RECEIVED LEFT DATA AFTER {time.time() - lt} SECONDS")

        rt = time.time()
        print("GETTING RIGHT DATA")
        right_data = get_data(2)
        print(f"RECEIVED RIGHT DATA AFTER {time.time() - rt} SECONDS")

        # Determine if there's a winner
        if left_data["status"] == DONE and right_data["status"] == DONE:
            if left_data["checkpoints"]["8"] < right_data["checkpoints"]["8"]:
                left_data["status"] = WIN
                right_data["status"] = LOSE
            else:
                right_data["status"] = WIN
                left_data["status"] = LOSE
        elif left_data["status"] == DONE:
            left_data["status"] = WIN
            right_data["status"] = LOSE
        elif right_data["status"] == DONE:
            right_data["status"] = WIN
            left_data["status"] = LOSE
        
        print("EMITTING DATA")
        socketio.emit("send_data", {"left": left_data, "right": right_data})
        print("DATA EMITTED")

@app.route("/")
def index():
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.on('connect')
def connect():
    socketio.start_background_task(background_thread)
    print('connecting')
    socketio.emit(
        "set_default", {"left_id": f"{DEFAULT_ID}", "right_id": f"{DEFAULT_ID}"}
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
