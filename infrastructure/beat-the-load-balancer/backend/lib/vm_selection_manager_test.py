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

import time

from base_cache import RedisSelectionManager
from vm_selection_manager import LocalSelectionManager


def test_selection_manager_basic():
    # test to check if SM can store and retrieve information
    s_mgr = LocalSelectionManager(vm_options=["vm-wh49"])
    vm_name = "vm-wh49"
    s_mgr.set_selected_vm(vm_name)
    assert s_mgr.get_selected_vm() == vm_name


def test_selection_manager_cache():
    # test to check if cache function is working fine or not
    s_mgr = LocalSelectionManager(vm_options=["vm-wh50"])
    vm_name = "vm-wh50"
    s_mgr.set_selected_vm(vm_name)
    time.sleep(2)
    assert s_mgr._is_selected_vm_recent() is False
    assert s_mgr.get_selected_vm() == vm_name
    assert s_mgr._is_selected_vm_recent() is True


def test_redis_selection_manager_basic():
    # test to check if SM can store and retrieve information
    s_mgr = RedisSelectionManager(vm_options=["vm-wh49"])
    vm_name = "vm-wh49"
    s_mgr.set_selected_vm(vm_name)
    assert s_mgr.get_selected_vm() == vm_name


def test_redis_selection_manager_cache():
    # test to check if cache function is working fine or not
    s_mgr = RedisSelectionManager(vm_options=["vm-wh50"])
    vm_name = "vm-wh50"
    s_mgr.set_selected_vm(vm_name)
    time.sleep(2)
    assert s_mgr._is_selected_vm_recent() is False
    assert s_mgr.get_selected_vm() == vm_name
    assert s_mgr._is_selected_vm_recent() is True
