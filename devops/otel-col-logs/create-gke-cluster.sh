#!/bin/bash
# Copyright 2024 Yoshi Yamaguchi
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

set -ex
gcloud container clusters create otel-collector-log-demo \
--region asia-east1 \
--release-channel rapid \
--logging SYSTEM,WORKLOAD \
--monitoring SYSTEM \
--preemptible \
--enable-autoprovisioning \
--max-cpu 16 \
--max-memory 32 \
--enable-autoscaling \
--max-nodes 1 \
--no-enable-ip-alias \
--scopes cloud-platform
