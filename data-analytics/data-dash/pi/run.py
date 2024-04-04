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

import argparse
import os
import time

from google.cloud import bigtable
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

from beam_break_sensor import BeamBreakSensor
from side_controller import SideController

parser = argparse.ArgumentParser()
parser.add_argument('--debug', help='Print to console')
parser.add_argument('--write-to-bt', help='Toggle writing to BT')

args = parser.parse_args()

debug = bool(args.debug)
write_to_bt = bool(args.write_to_bt)

PINS = [i for i in range(19, 27)]
LEFT_CARDS = {1,2}
RIGHT_CARDS = {3,4}
DEFAULT_ID = 999999999999

side_controller = SideController()

project_id = os.environ["PROJECT_ID"]
instance_id = os.environ["BIGTABLE_INSTANCE"]
lookup_table_id = os.environ["BIGTABLE_LOOKUP_TABLE"]
race_table_id = os.environ["BIGTABLE_RACE_TABLE"]

client = bigtable.Client(project=project_id)
instance = client.instance(instance_id)
lookup_table = instance.table(lookup_table_id)
race_table = instance.table(race_table_id)

try:
    GPIO.setmode(GPIO.BCM)
    sensors = [BeamBreakSensor(i, pin, race_table,
                debug=debug, write_to_bt=write_to_bt) \
               for i, pin in enumerate(PINS, start=1)]

    reader = SimpleMFRC522()

    last_scan = 0
    RFID_WAIT = 3

    car_side_map = {
        side_controller.LEFT_CONST: "car1",
        side_controller.RIGHT_CONST: "car2",
    }

    side = side_controller.get_side()

    car_id = DEFAULT_ID
    
    print(f"STARTING SIDE: {car_side_map[side]}")
    while True:
        _time = time.time()
        id = reader.read_id_no_block()

        # Check if ID controls Pi sides for webapp
        if side_controller.is_side(id):
            side = side_controller.get_side()

        if id and _time - last_scan > RFID_WAIT:
            print(id)
            car_id = id
            last_scan = _time
            
            row = lookup_table.direct_row(car_side_map(side))
            row.set_cell("cf", "id", str(car_id))
            row.commit()

        for sensor in sensors:
            sensor.read(car_id)
finally:
    GPIO.cleanup()
