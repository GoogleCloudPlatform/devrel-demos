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

# Shared make variables and targets for every episode. Include it from an
# episode Makefile after setting EP (two digits).

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
-include $(ROOT)/shared/infra/.env
export

.DEFAULT_GOAL := help

PY ?= python3
KUBECTL ?= kubectl
TTL ?= 3d
DRY_RUN ?= 0
FAKE_MODEL ?= 0
CLUSTER_PREFIX ?= k8s-revisited
REGION ?= us-central1
ZONE ?= $(REGION)-a
LABELS := series=k8s-revisited,episode=ep$(EP),ttl=$(TTL)
PYPATH := $(ROOT)/shared/bench:$(ROOT)/shared/agent-check
RESULTS := results
# The agent check uses its own virtualenv (make agent-venv) when it exists.
AGENT_VENV := $(ROOT)/shared/agent-check/.venv
AGENT_PY ?= $(if $(wildcard $(AGENT_VENV)/bin/python),$(AGENT_VENV)/bin/python,$(PY))

# Prefix commands with $(RUN) so DRY_RUN=1 prints them instead of running them.
RUN = $(if $(filter 1,$(DRY_RUN)),@echo "[dry-run]",)

.PHONY: help require-project agent-check report verify env

help: ## Show this episode's targets
	@echo "Episode ep$(EP) targets:"
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sed 's/^/  /'

require-project:
	@test -n "$(PROJECT_ID)" || { echo "PROJECT_ID is not set: copy shared/infra/env.example to shared/infra/.env"; exit 2; }

env: ## Capture the run environment into results/env.json
	@mkdir -p $(RESULTS)
	$(RUN) env PYTHONPATH=$(PYPATH) $(PY) -m k8s_revisited_bench.envinfo --out $(RESULTS)/env.json $(if $(CONTEXT),--context $(CONTEXT),)

agent-check: ## Run this episode's agent check (FAKE_MODEL=1: offline pipeline test, no cluster or model calls)
	@mkdir -p $(RESULTS)
	$(RUN) env PYTHONPATH=$(PYPATH) $(AGENT_PY) -m agent_check --ep $(EP) --out $(RESULTS)/agent-check.csv $(if $(filter 1,$(FAKE_MODEL)),--fake-model,$(if $(KUBE_CONTEXT),--context $(KUBE_CONTEXT),)) $(AGENT_CHECK_ARGS)

report: ## Render results.md from the CSVs in results/
	$(RUN) env PYTHONPATH=$(PYPATH) $(PY) -m k8s_revisited_bench.report $(RESULTS)

verify: ## Static checks for the whole folder
	$(ROOT)/tools/verify.sh
