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
import os
import time


class JobFileManager:
    """Class to manage the temporary file used to track job status.

    (Optional) Use `expiry_time` flag, to set up timeout for the job.
    """

    def __init__(self, filename, expiry_time=None) -> None:
        self.flag_file = filename
        self.expiry_time = expiry_time

    def __repr__(self) -> str:
        return f"JobFileManager({self.flag_file}, {self.expiry_time})"

    def __str__(self) -> str:
        return f"JobFileManager({self.flag_file}, {self.expiry_time})"

    def is_running_job(self) -> bool:
        return self.is_job_running()

    def is_file_recent(self) -> bool:
        if os.path.isfile(self.flag_file):
            with open(self.flag_file, "r") as f:
                timestamp = float(f.read())
                return abs(time.time() - timestamp) <= 60
        else:
            logging.warning(f"JobFileManager: Found no file({self.flag_file})")
        return False

    def is_job_running(self) -> bool:
        """Checks if the job is still running by checking for the temporary file.

        If `expiry_time` is set and the timestamp in the file with in the given expiry_time time
         then the job is considered to be still running.

        Returns
            bool: True if the job is still running, False otherwise.
        """
        logging.info(f"JobFileManager: Check for temporary file {self.flag_file}!")
        if not self.expiry_time:
            return os.path.isfile(self.flag_file)
        return self.is_file_recent()

    def create_timestamp_file(self) -> bool:
        """Creates a timestamp file with the current time."""
        logging.info(f"JobFileManager: Check for temporary file {self.flag_file}!")
        if self.is_job_running():
            return False
        else:
            logging.info(f"JobFileManager: Creating temporary file {self.flag_file}!")
            fp = open(self.flag_file, "w")
            fp.write(str(time.time()))
            return True

    def delete_timestamp_file(self) -> bool:
        """Deletes the timestamp file if it exists."""
        if os.path.isfile(self.flag_file):
            os.remove(self.flag_file)
            logging.info(f"JobFileManager: Clearing temporary file {self.flag_file}!")
        else:
            logging.info(
                f"JobFileManager: Clearing temporary {self.flag_file} is not required!"
            )
        return True
