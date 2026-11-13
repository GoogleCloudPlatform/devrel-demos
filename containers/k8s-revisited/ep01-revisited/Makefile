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

EP := 01
include ../shared/make/common.mk

RAPID     := $(CLUSTER_PREFIX)-ep01-rapid
STABLE    := $(CLUSTER_PREFIX)-ep01-stable
AUTOPILOT := $(CLUSTER_PREFIX)-ep01-autopilot

# Context names written by `gcloud container clusters get-credentials`.
# Standard clusters are zonal; Autopilot clusters are regional.
CTX_RAPID     := gke_$(PROJECT_ID)_$(ZONE)_$(RAPID)
CTX_STABLE    := gke_$(PROJECT_ID)_$(ZONE)_$(STABLE)
CTX_AUTOPILOT := gke_$(PROJECT_ID)_$(REGION)_$(AUTOPILOT)
CONTEXTS ?= $(CTX_RAPID) $(CTX_STABLE) $(CTX_AUTOPILOT)

# env.json and the agent check's server-side dry-run use the Rapid cluster.
CONTEXT ?= $(CTX_RAPID)
KUBE_CONTEXT ?= $(CTX_RAPID)

.PHONY: up run stretch down

up: require-project ## Create the Rapid and Stable Standard clusters, the swap node pool, and the Autopilot cluster
	$(RUN) ../shared/infra/gke-cluster.sh create --episode ep01 --name $(RAPID) --channel rapid --ttl 1d
	$(RUN) ../shared/infra/gke-nodepool.sh create --episode ep01 --cluster $(RAPID) --pool swap \
	  --machine-type e2-standard-4 --system-config infra/system-config/swap.yaml --ttl 1d -- \
	  --node-taints gke-swap=enabled:NoSchedule
	$(RUN) ../shared/infra/gke-cluster.sh create --episode ep01 --name $(STABLE) --channel stable --ttl 1d
	$(RUN) ../shared/infra/gke-cluster.sh create --episode ep01 --name $(AUTOPILOT) --channel rapid --autopilot --ttl 1d

run: require-project env ## Core experiments: census, census knobs, the 2020 diff and the five demos, on each cluster
	$(RUN) ./bench/compare-channels.sh $(CONTEXTS)

stretch: ## Ep1 has no stretch experiments
	@echo "Ep1 has no stretch experiments."

down: require-project ## Delete the three clusters (the swap node pool goes with the Rapid cluster)
	$(RUN) ../shared/infra/gke-cluster.sh delete --episode ep01 --name $(RAPID)
	$(RUN) ../shared/infra/gke-cluster.sh delete --episode ep01 --name $(STABLE)
	$(RUN) ../shared/infra/gke-cluster.sh delete --episode ep01 --name $(AUTOPILOT)
