#!/usr/bin/env python

# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import time


class LocalSelectionManager:
    """
    SelectionManager to store
     * Player's VM selection of VM
    """

    def __init__(self, vm_options):
        # Write VM selection information to disk
        self.filename = "/tmp/flask_app_player_vm_selection.log"
        # expected
        self.vm_options = vm_options
        # Temp cache variables to stop VM
        self.selected_vm = None
        self.last_updated_time = 0
        # cache time limit in seconds
        self._cache_time_limit = 1
        logging.info(f"Started {__class__}")

    def _read_selected_vm_from_storage(self, vm_name=None):
        "Read the VM Name from OS file"
        if vm_name is None:
            with open(self.filename) as fp:
                vm_name = fp.read().strip()
        # update config
        self.selected_vm = vm_name
        self.last_updated_time = time.time()

    def _write_selected_vm_to_storage(self, vm_name):
        "Write the VM Name from OS file"
        with open(self.filename, "w") as fp:
            fp.write(vm_name)

    def _is_selected_vm_recent(self):
        "Return true if cache is updated less than a 1 second ago"
        return (time.time() - self.last_updated_time) < self._cache_time_limit

    def __refresh_vm_selection(self):
        if not self._is_selected_vm_recent():
            self._read_selected_vm_from_storage()

    def __repr__(self):
        self.__refresh_vm_selection()
        return f"{self.selected_vm}"

    def set_selected_vm(self, vm_name) -> None:
        assert vm_name in self.vm_options
        self._write_selected_vm_to_storage(vm_name=vm_name)
        self._read_selected_vm_from_storage(vm_name=vm_name)

    def get_selected_vm(self) -> str:
        self.__refresh_vm_selection()
        return self.selected_vm
