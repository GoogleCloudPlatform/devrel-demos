#!/bin/bash

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


echo "🔧 Setting up the AlloyDB Provisioner..."

# 1. Ensure the creation script is executable
chmod +x create_alloydb.sh

# 2. Install Flask (swallows errors if dependencies conflict, to use pre-installed versions)
pip install -r requirements.txt --quiet || echo "⚠️ Dependency warning: Attempting to run with existing packages..."

echo "✅ Setup complete."
echo "🚀 Starting Server on Port 8080..."
echo "👉 Click the 'Web Preview' button in Cloud Shell top right -> 'Preview on port 8080'"

# 3. Run the application
python3 main.py
