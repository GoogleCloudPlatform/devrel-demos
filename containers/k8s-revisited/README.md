# Kubernetes, Revisited (on GKE)

Code for a series that looks at what changed in Kubernetes between 2020 and 2026 for agent and GenAI workloads. Each episode explains a feature from the upstream Kubernetes source and tries it on Google Kubernetes Engine (GKE).

Each episode folder is a runbook: `make up`, `make run`, `make report`, `make down`. Results land in the episode's `results/` folder, which is gitignored, so your measurements stay on your machine.

> Status: episodes are added here as they're published. Anything not yet checked against a primary source is marked `VERIFY`.

## Episodes

| # | Folder | Topic |
|---|---|---|
| 1 | [ep01-revisited](ep01-revisited/) | What changed from 2020 to 2026, read from GKE clusters with `census`, plus five features to try |

## Prerequisites

- A Google Cloud project with billing turned on, where you can create GKE clusters
- The Google Cloud CLI with `gke-gcloud-auth-plugin`, signed in with `gcloud auth login`
- kubectl 1.37 or later (`make tools` installs pinned versions of kubectl and the other CLI tools into `~/.local/bin`)
- Go 1.26 or later, and Python 3.12 or later with PyYAML

## Quick start

```bash
cp shared/infra/env.example shared/infra/.env   # then set PROJECT_ID
make verify                  # static checks and offline self-tests, no cloud access
make ep01-up                 # create the Ep1 clusters
make ep01-run                # run the Ep1 experiments, writing ep01-revisited/results/
make ep01-down               # delete everything Ep1 created
./shared/infra/reaper.sh --check
```

Episode targets accept `DRY_RUN=1`, which prints the commands instead of running them.

## Cost and teardown

Clusters are labeled `series=k8s-revisited,episode=epNN,ttl=<duration>`. `make epNN-down` deletes what an episode created, and `shared/infra/reaper.sh --check` lists anything left behind. See [docs/cost-and-teardown.md](docs/cost-and-teardown.md).

## How measurements work

See [docs/methodology.md](docs/methodology.md). The per-episode agent check, which tests whether a coding agent can write that episode's Kubernetes config for GKE, is described in [docs/agent-check.md](docs/agent-check.md).

## Layout

```text
docs/        methodology, cost and teardown, the agent check
shared/      make include, GKE infra scripts, bench helpers, agent check, the Kubernetes 1.37 context file
tools/       verify.sh (static checks, self-tests, leak check)
epNN-*/      one folder per episode: README runbook, Makefile, manifests/, bench/, results/
```

This is not an officially supported Google product.
