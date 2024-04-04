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

from google.cloud import bigtable
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

from beam_break_sensor import BeamBreakSensor
from side_controller import SideController

# Pins as mapped to the Pis
PINS = [i for i in range(19, 27)]

# Subtract current_time from this value to get rows ordered last to first
MAX_VALUE = 9999999999

# Reset rowkey if the last RFID read was N seconds ago
ROWKEY_RESET = 30

# Read RFID every N seconds
RFID_WAIT = 3

# Load args
project_id = os.environ["PROJECT_ID"]
instance_id = os.environ["BIGTABLE_INSTANCE"]
lookup_table_id = os.environ["BIGTABLE_LOOKUP_TABLE"]
race_table_id = os.environ["BIGTABLE_RACE_TABLE"]

# Bigtable objects
client = bigtable.Client(project=project_id)
instance = client.instance(instance_id)
lookup_table = instance.table(lookup_table_id)
race_table = instance.table(race_table_id)

try:
    # Initialize Pi connections to read as BCM
    GPIO.setmode(GPIO.BCM)

    # Initialize sensors
    sensors = [BeamBreakSensor(i, pin, race_table,) \
               for i, pin in enumerate(PINS, start=1)]

    # Initialize RFID sensor
    reader = SimpleMFRC522()

    # SideController controls if this Pi should 
    side_controller = SideController()

    # Column mappings of side_controller
    car_side_map = {
        side_controller.LEFT_CONST: "car1",
        side_controller.RIGHT_CONST: "car2",
    }

    # Initialize the "side" of the webapp this Pi streams
    side = side_controller.get_side()

    id = None
    rowkey = None
    last_scan = 0
    last_seen = 0

    print(side)
    print(f"STARTING SIDE: {car_side_map[side]}")
    while True:
        _time = time.time()

        if _time - last_seen > ROWKEY_RESET:
            rowkey = None

        # Only accept RFID reads after a certain period
        if _time - last_scan > RFID_WAIT:
            id = reader.read_id_no_block()
            last_scan = _time
            if id:
                last_seen = _time
                rowkey = f"{id}#{MAX_VALUE - _time}"
                print(f"CAR ID: {rowkey}")

        # If there is an ID and the ID does not update the Pi sides
        if id and not side_controller.is_side(id):
            # Write scanned ID to lookup table
            row = lookup_table.direct_row(car_side_map[side])
            row.set_cell("cf", "id", str(id))
            row.commit()

        # Poll sensors
        if rowkey:
            for sensor in sensors:
                sensor.read(rowkey)
finally:
    GPIO.cleanup()
