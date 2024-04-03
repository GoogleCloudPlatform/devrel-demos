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

class SideController:
    STATE_FILE = "state.txt"

    LEFT_CONST = 0
    RIGHT_CONST =  0
    
    LEFT_CARDS = {
        1,
        2
    }
    RIGHT_CARDS = {
        3,
        4
    }

    def __init__(self):
        if os.path.isfile(self.STATE_FILE):
            with open("state.txt") as f:
                self.side = f.readline()
        else:
            self.side = LEFT_CONST

    def set_side(self, id):
        if id in self.LEFT_CARDS:
            self.side = LEFT_CONST
            print("SIDE SET TO LEFT")
        else:
            self.side = RIGHT_CONST
            print("SIDE SET TO RIGHT")
        
        with open(self.STATE_FILE, "w") as f:
            f.writelines(self.side)

    def get_side(self):
        return self.side
    
    def is_side(self, id):
        if id in self.LEFT_CARDS or id in self.RIGHT_CARDS:
            self.set_side(id)