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

# A script to run the multi-threaded ComputeEngineEventGen Java application.
# Configurable with environment variables.

echo "Building the project..."
mvn clean install -P compute-engine-client

# --- Configuration (with sensible defaults) ---
JAR_PATH="./target/kafka-quickstart-1.0-SNAPSHOT.jar"
NUM_THREADS="${NUM_THREADS:-4}"
TOPIC="${TOPIC:-test_topic}"
SCENARIO="${SCENARIO:-DEFAULT}"
NUM_ITERATIONS="${NUM_ITERATIONS:-10000}"
SESSIONS_PER_ITERATION="${SESSIONS_PER_ITERATION:-10}"
BYTES_PER_ITERATION="${BYTES_PER_ITERATION:-100000}"

# --- Build the Java command ---
JAVA_CMD="java -Xms16g -Xmx16g \
  -DprojectId=${PROJECT_ID} \
  -DnumThreads=${NUM_THREADS} \
  -Dtopic=${TOPIC} \
  -Dscenario=${SCENARIO} \
  -DnumIterations=${NUM_ITERATIONS} \
  -DsessionsPerIteration=${SESSIONS_PER_ITERATION} \
  -DbytesPerIteration=${BYTES_PER_ITERATION} \
  -jar ${JAR_PATH}"

# --- Execute the command ---
echo "Running command:"
echo "${JAVA_CMD}"
eval "${JAVA_CMD}"
