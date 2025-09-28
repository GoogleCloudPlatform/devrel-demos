# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth

def get_project_id():
    """
    Gets the project ID.

    The project ID is retrieved in the following order of precedence:
    1. The PROJECT_ID environment variable (loaded from .env if
       present).
    2. The project ID from the Google Cloud environment (via
       google-auth).

    Raises:
        ValueError: If the project ID cannot be determined.
    """
    project_id = os.getenv('PROJECT_ID')
    if project_id:
        return project_id
    try:
        _, project_id = google.auth.default()
        if project_id:
            return project_id
    except google.auth.exceptions.DefaultCredentialsError:
        pass
    raise ValueError(
        "Could not determine the project ID. "
        "Please set the PROJECT_ID environment variable in a .env file for "
        "local development, or ensure the application is running in a "
        "Google Cloud environment."
    )