# Copyright 2025 Google LLC
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

FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the workdir and copy requirements.txt
WORKDIR /app
COPY requirements.txt .

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED=1

# Prepare virtual environment path
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
RUN uv venv /opt/venv && uv pip install -U -r requirements.txt

# Copy the application code
COPY . .

# Set host and port
ENV HOST 0.0.0.0
EXPOSE $PORT

# Run the FastMCP server
CMD ["python3", "main.py"]
