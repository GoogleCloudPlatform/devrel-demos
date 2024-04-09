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

import time
import RPi.GPIO as GPIO

class BeamBreakSensor:
    broken_time = 0
    unbroken_time = 0
    is_broken = False
    rowkey = None
    COLUMN_FAMILY = "cf"
    SENSOR_READ_INTERVAL = 10
    def __init__(self, id, pin, table=None, meta_table=None):
        self.init_time = time.time()
        self.id = id
        self.pin = pin
        self.table = table
        self.meta_table = meta_table
        self.init_pin()

    def init_pin(self):
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # write initial sensor value to meta table
        rowkey = f"sensors#{self.init_time}"
        row = self.meta_table.direct_row(rowkey)
        gpio_input = GPIO.input(self.pin)
        row.set_cell(self.COLUMN_FAMILY, self.pin, gpio_input)
        print(f"initializing sensor {self.id} (pin {self.pin}) with value {gpio_input}")
        row.commit()

    def read(self, rowkey):
        self.rowkey = rowkey
        _read = GPIO.input(self.pin)
        _time = time.time()
        self.unbroken(_time) if _read else self.broken(_time)

    def broken(self, cur_time):
        # Return if state is already broken.
        if self.is_broken:
            return

        print(f"SENSOR {self.id}: BROKEN")
        self.is_broken = True

        if cur_time - self.broken_time > self.SENSOR_READ_INTERVAL:
            self.broken_time = cur_time
            self.upload(cur_time, True)

    def unbroken(self, cur_time):
        self.unbroken_time = cur_time
        if self.is_broken:
            self.upload(cur_time, False)
            print(f"SENSOR {self.id}: UNBROKEN")
            self.is_broken = False

    def upload(self, cur_time, broken):
        col = f"t{self.id}_s" if broken else f"t{self.id}_e"

        row = self.table.direct_row(self.rowkey)
        row.set_cell(self.COLUMN_FAMILY, col, str(cur_time))
        row.commit()
