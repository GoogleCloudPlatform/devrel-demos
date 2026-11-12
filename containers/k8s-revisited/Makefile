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

SHELL := /bin/bash
.DEFAULT_GOAL := help

EP ?=

.PHONY: help tools agent-venv verify agent-check

help: ## Show the top-level targets
	@echo "Top-level targets:"
	@grep -E '^[a-zA-Z_-]+:.*## ' $(firstword $(MAKEFILE_LIST)) | sed -E 's/:.*## /\t/' | sed 's/^/  /'
	@echo "Episode targets: make epNN-<up|run|stretch|agent-check|report|down> (for example make ep01-up)"

tools: ## Install pinned kind, kubectl, helm, kwok and kubeconform into ~/.local/bin (needs network)
	./shared/infra/tools-install.sh

agent-venv: ## Create shared/agent-check/.venv with google-adk for real agent-check runs (needs network)
	python3 -m venv shared/agent-check/.venv
	shared/agent-check/.venv/bin/pip install -r shared/agent-check/requirements.txt

verify: ## Static checks, offline self-tests and the leak check
	./tools/verify.sh

agent-check: ## Run one episode's agent check: make agent-check EP=01 [FAKE_MODEL=1]
	@test -n "$(EP)" || { echo "usage: make agent-check EP=NN [FAKE_MODEL=1]"; exit 2; }
	$(MAKE) ep$(EP)-agent-check

ep%:
	@stem='$*'; num="ep$${stem%%-*}"; action="$${stem#*-}"; \
	dir=$$(ls -d $${num}-*/ 2>/dev/null | head -n1); \
	if [ -z "$$dir" ] || [ "$$action" = "$$stem" ]; then \
	  echo "usage: make epNN-<up|run|stretch|agent-check|report|down|verify>"; exit 2; fi; \
	$(MAKE) -C "$$dir" "$$action"
