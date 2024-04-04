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
    car_id = None

    def __init__(self, id, pin, table=None):
        self.id = id
        self.pin = pin
        self.table = table
        self.init_pin()

    def init_pin(self):
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def read(self, car_id):
        self.car_id = car_id
        _read = GPIO.input(self.pin)
        _time = time.time()
        self.unbroken(_time) if _read else self.broken(_time)

    def broken(self, cur_time):
        if not self.is_broken:
            print(f"SENSOR {self.id}: BROKEN")
            self.is_broken = True
            if cur_time - self.broken_time > 10:
                self.broken_time = cur_time
                self.upload(cur_time)

    def unbroken(self, cur_time):
        self.unbroken_time = cur_time
        if self.is_broken:
            print(f"SENSOR {self.id}: UNBROKEN")
            self.is_broken = False

    def upload(self, cur_time):
        print((self.car_id, self.id, self.broken_time))

        column_family_id = "cf"

        row = self.table.direct_row(f"{self.car_id}#{cur_time}")
        row.set_cell(column_family_id, f"cp{self.id}", str(cur_time))
        row.commit()

#        self.calculate_speed()

    def calculate_speed(self):
        print(float(self.unbroken_time - self.broken_time) / 2.5)
