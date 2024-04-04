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

# Side controller controls the side of the webapp that the Pis stream to

import os

class SideController:
    STATE_FILE = "state.txt"

    LEFT_CONST = 0
    RIGHT_CONST =  1

    LEFT_CARDS = {
        173448457841
    }
    RIGHT_CARDS = {
        769013855813
    }

    def __init__(self):
        if os.path.isfile(self.STATE_FILE):
            with open("state.txt") as f:
                self.side = int(f.readline().strip())
        else:
            self.side = self.LEFT_CONST

    def set_side(self, id):
        if id in self.LEFT_CARDS:
            self.side = self.LEFT_CONST
            print("SIDE SET TO LEFT")
        else:
            self.side = self.RIGHT_CONST
            print("SIDE SET TO RIGHT")        
        with open(self.STATE_FILE, "w") as f:
            f.writelines([str(self.side)])

    def get_side(self):
        return self.side
    
    def is_side(self, id):
        if id in self.LEFT_CARDS or id in self.RIGHT_CARDS:
            self.set_side(id)
            return True