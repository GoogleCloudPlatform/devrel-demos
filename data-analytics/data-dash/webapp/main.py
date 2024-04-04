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
import time

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
ERR =  3

COLORS ={
    OK: "yellow",
    DONE: "green",
    WIN: "rgb(0, 255, 0)",
    ERR: "red",
}

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
    _dt_end = (datetime.datetime.now(datetime.UTC)
                 - datetime.timedelta(seconds=RESET_ID_TIMEOUT))
    _cells = {}
    rows = lookup_table.read_rows()
    for row in rows:
        _row_key = row.row_key.decode("utf-8")
        _cells[_row_key] = (
            row.cells["cf"][b"id"][0].value.decode("utf-8"),
            row.cells["cf"][b"id"][0].timestamp,
        )
    if not _cells:
        return (DEFAULT_ID, DEFAULT_ID)
    elif _cells["car1"][1] > _dt_end or _cells["car2"][1] > _dt_end:
        return (
            _cells["car1"][0],
            _cells["car2"][0],
        )
    else:
        return (DEFAULT_ID, DEFAULT_ID)

def get_status():
    _cells = {}
    _times = {}
    rows = race_table.read_rows(limit=2)
    for row in rows:
        id, ts =row.row_key.decode("utf-8").split("#")
        _times[id] = ts
        row_cells = row.cells["cf"]
        if row.cells["cf"][b"cp8"][0].value.decode("utf-8"):
            _cells[id] = (DONE, None)
        elif time.time() - ts > CAR_ERR_TIMEOUT:
            if (row_cells.get(b"t1_s") or
                row_cells.get(b"t2_s") or
                row_cells.get(b"t3_s")):
                for i in reversed(range(1,9)):
                    val = row_cells.get(b"" + f"t{i}_s")
                    if val:
                        _cells[id] = (ERR, val[0].value.decode("utf-8"))
        else:
            _cells[id] = (OK, None)

        c1, c2 = _cells.keys()
    if _cells[c1][0] == DONE and _cells[c2][0] == DONE:
        if _times[c1] < _times[c2]:
            _cells[c1][0] = WIN
        else:
            _cells[c2][0] = WIN
    return _cells

def background_thread():
    while True:
        socketio.sleep(1)
        left_id, right_id, car_ids = get_ids()
        print(left_id, right_id, flush=True)
        socketio.emit("set_pictures", {"left_id": left_id, "right_id": right_id})
        
        left_status = None
        right_status = None
        left_data = None
        right_data = None
        
        if left_id == DEFAULT_ID:
            left_status = OK
        if right_id == DEFAULT_ID:
            right_status = OK

        if not status or not status:
            status = get_status()
        
            if not left_status:
                left_status, left_data = status[left_id]

            if not right_status:
                right_status, right_data = status[right_id]

        socketio.emit("set_status", 
            {"left_color": COLORS[left_status],
             "right_color": COLORS[left_status],
             "left_data": left_data,
             "right_data": right_data})

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
