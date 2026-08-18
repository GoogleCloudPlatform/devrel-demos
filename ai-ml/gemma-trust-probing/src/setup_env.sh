#!/usr/bin/env bash

# Copyright 2026 Google LLC
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

set -e

echo "=== Project Lantern: Environment Setup ==="
echo "Working directory: $(pwd)"

# 1. Select Python binary (prefer /usr/bin/python3 for PyTorch compatibility)
if [ -f "/usr/bin/python3" ]; then
    PYTHON_BIN="/usr/bin/python3"
else
    PYTHON_BIN="python3"
fi

echo "Using Python: $($PYTHON_BIN --version)"

# 2. Create virtualenv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    $PYTHON_BIN -m venv venv
else
    echo "Virtual environment 'venv' already exists."
fi

# 3. Activate venv
source venv/bin/activate

# 4. Upgrade pip and install requirements
echo "Installing dependencies..."
pip install --upgrade pip --index-url https://pypi.org/simple
pip install --index-url https://pypi.org/simple -r requirements.txt

echo ""
echo "=== Environment Setup Complete ==="
echo "To activate manually: source venv/bin/activate"
