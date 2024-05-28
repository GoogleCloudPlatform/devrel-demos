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
import subprocess

from lib import config
from lib.base_cache import RedisHelper


class SystemIPConfig(RedisHelper):
    """
    Handles system IP configuration.
    """

    def __init__(self):
        super().__init__()

        self.host_ip = ""
        self.host_ip_key = f"{config.HOSTNAME}_IP".lower()

        self.host_internal_ip = ""
        self.host_internal_ip_key = f"{config.HOSTNAME}_INTERNAL_IP".lower()

        self.host_external_ip = ""
        self.host_external_ip_key = f"{config.HOSTNAME}_EXTERNAL_IP".lower()

    @staticmethod
    def get_host_ip_address(command):
        ip_address = "0.0.0.0"
        if config.IS_RUNNING_IN_LOCAL:
            ip_address = "0.0.0.0"
        else:
            try:
                ip_address = subprocess.check_output(command, shell=True)
            except Exception:
                logging.exception(f"Failed to run --->  get_host_ip_address({command})")
        return ip_address

    def update_ip_address(self):
        """
        Updates the system IP configuration.
        """
        command_for_internal_ip = 'curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/network-interfaces/0/ip'
        command_for_external_ip = 'curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip'

        # collect ip config
        self.host_internal_ip = self.get_host_ip_address(command_for_internal_ip)
        self.host_external_ip = self.get_host_ip_address(command_for_external_ip)
        self.host_ip = self.host_external_ip
        # update ip
        self.set(self.host_ip_key, self.host_ip)
        self.set(self.host_internal_ip_key, self.host_internal_ip)
        self.set(self.host_external_ip_key, self.host_external_ip)

    def get_system_config(self):
        """
        Returns the system configuration.
        """
        self.update_ip_address()
        return {
            # "host_ip": self.host_ip,
            # "host_internal_ip": self.host_internal_ip,
            "host_external_ip": self.host_external_ip,
        }
