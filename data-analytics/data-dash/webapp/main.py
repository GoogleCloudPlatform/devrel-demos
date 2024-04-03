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

import datetime
import os
from threading import Lock

from flask import Flask, render_template
from flask_socketio import SocketIO
from google.cloud import bigtable

async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

DEFAULT_ID = 999999999999

project_id = os.environ["PROJECT_ID"]
instance_id = "testing-instance"
lookup_table_id = "data_dash_lookup"
race_table_id = "data_dash_live_test"

client = bigtable.Client(project=project_id)
instance = client.instance(instance_id)
lookup_table = instance.table(lookup_table_id)
race_table = instance.table(race_table_id)
column_family_id = "cf"


def get_ids():
    _dt_end = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=30)
    _cells = {}
    rows = lookup_table.read_rows()
    for row in rows:
        _cells[row.row_key.decode("utf-8")] = (
            row.cells["cf"][b"id"][0].value.decode("utf-8"),
            row.cells["cf"][b"id"][0].timestamp,
        )
    if not _cells:
        return (DEFAULT_ID, DEFAULT_ID)
    if _cells["car1"][1] > _dt_end or _cells["car2"][1] > _dt_end:
        return (
            _cells["car1"][0],
            _cells["car2"][0],
        )
    else:
        return (DEFAULT_ID, DEFAULT_ID)


def background_thread():
    while True:
        socketio.sleep(1)
        left_id, right_id = get_ids()
        print(left_id, right_id, flush=True)
        socketio.emit("set_pictures", {"left_id": left_id, "right_id": right_id})


@app.route("/")
def index():
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    left_id, right_id = get_ids()
    socketio.emit(
        "set_pictures", {"left_id": f"{DEFAULT_ID}", "right_id": f"{DEFAULT_ID}"}
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
