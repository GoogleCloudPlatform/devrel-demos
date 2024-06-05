#Copyright 2023 Google LLC
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import subprocess


def copy_image(image_tag, source_repository_name, target_repository_name):
    command = "gcrane cp {0}/{1} {2}/{1}".format(source_repository_name, image_tag, target_repository_name)
    #command = command_format.format(image_tag, ar_repository_name)
    print(f"command: {command}", flush=True)
    try:
        completedProcess = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600, universal_newlines=True)
        print(f"completedProcess: {completedProcess}", flush=True)
        return completedProcess
    except subprocess.TimeoutExpired as e:
        print(f"Subprocess error: {e}", flush=True)
        raise e
