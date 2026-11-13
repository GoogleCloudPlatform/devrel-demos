# Ep01: Kubernetes, Revisited on GKE: what changed from 2020 to 2026, for agents

> Valid as of: Kubernetes 1.37.x · GKE versions recorded in `results/env.json` and `results/census.md` · Teardown: `make down`

A snapshot of what a 2026 GKE cluster can do that a 2020 cluster couldn't, read with `census` from three clusters (Rapid and Stable Standard clusters, and an Autopilot cluster), plus five features that graduated while many of us weren't looking, each with a check that it does what it claims.

## What you'll see

- Served APIs, named capabilities, RuntimeClasses and feature gates, side by side for each cluster (`results/census.md`).
- The effective kubelet configuration and kubelet feature gates for each node pool (`results/knobs.md`).
- A `git diff 2020..2026` table for each cluster, against a hand-written Kubernetes 1.19 snapshot (`results/diff-2020-<context>.md`).
- Native sidecars, in-place resize, image volumes, user namespaces and swap on each cluster, with a functional check for each (`results/five-things.csv`).

## Prerequisites

- A Google Cloud project with billing and the Kubernetes Engine API turned on, set in `../shared/infra/.env` (copy `../shared/infra/env.example`)
- The Google Cloud CLI with `gke-gcloud-auth-plugin`, kubectl 1.37 or later, and Go 1.26 or later
- Permission to create clusters and to read nodes through the API server's node proxy (`nodes/proxy`)

## Run it

```bash
make up        # Rapid and Stable Standard clusters, a swap node pool on the Rapid cluster, and an Autopilot cluster
make run       # census, census knobs, the 2020 diff and the five demos on each cluster
make report    # render results.md from the CSVs
make down      # delete the three clusters
../shared/infra/reaper.sh --check
```

Add `DRY_RUN=1` to any target to print the commands instead of running them. An Autopilot cluster starts with no nodes, so `make run` first starts a small `census-keepalive` Pod there and deletes it at the end. Each demo waits up to 10 minutes for its Pod (`READY_TIMEOUT`, in seconds). If `make down` finds another operation running on a cluster, such as an Autopilot upgrade, it waits for it and retries.

## Core experiments

1. `census` on each cluster: APIs served, named capabilities, RuntimeClasses, feature gates, and the features each node declares. Each cluster is also compared with the 2020 baseline.
2. `census knobs`: the effective kubelet configuration and kubelet feature gates per node pool, read from `/configz` and `/metrics` through the node proxy.
3. The five demos on each cluster. Each one goes through a server-side dry-run, an apply, and a check of the behavior itself:
   - sidecar: the init container with `restartPolicy: Always` started before the app and keeps running
   - resize: the CPU request changes through the `resize` subresource without a container restart
   - image volume: the OCI artifact shows up read-only at `/models`
   - user namespaces: `/proc/self/uid_map` shows root in the container mapped to an unprivileged host UID
   - swap: on the swap node pool, a Pod that goes past its memory limit keeps running, while the same Pod on a pool without swap is OOMKilled. This demo runs only on clusters with a node pool named `swap`.

## Stretch experiments

None for this episode.

## Expected results

From our runs in November 2026 (GKE 1.37.1-gke.2097000 on Rapid and Autopilot, 1.35.8-gke.1796000 on Stable):

- On both Standard clusters, the sidecar, resize, image volume and user namespaces demos pass, and the swap demo passes on the Rapid cluster's swap pool.
- On Autopilot, the sidecar passes and the other demos don't run as written. See Troubleshooting.
- No cluster serves the Workload or PodGroup API, because the `GenericWorkload` feature gate is off. All three serve DRA (`resource.k8s.io/v1`).

Your results can differ as GKE versions move.

## Under the hood

- [pkg/kubelet/pod_workers.go](https://github.com/kubernetes/kubernetes/tree/v1.37.0/pkg/kubelet/pod_workers.go) and [pkg/kubelet/pleg](https://github.com/kubernetes/kubernetes/tree/v1.37.0/pkg/kubelet/pleg)
- [pkg/kubelet/cm](https://github.com/kubernetes/kubernetes/tree/v1.37.0/pkg/kubelet/cm): the CPU, memory, topology and DRA managers
- [staging/src/k8s.io/cri-api](https://github.com/kubernetes/kubernetes/tree/v1.37.0/staging/src/k8s.io/cri-api): CRI v1
- [pkg/features/kube_features.go](https://github.com/kubernetes/kubernetes/tree/v1.37.0/pkg/features/kube_features.go): feature gates and their maturity

## Friction and workarounds

- An Autopilot cluster has no nodes until a workload asks for one, so `make run` starts a small `census-keepalive` Pod first.
- `census knobs` can't read the kubelet configuration on Autopilot, because Autopilot doesn't allow the `nodes/proxy` permission. Node features still show up in `results/census.md`.
- `make down` can hit "Cluster is running incompatible operation" on Autopilot. It waits for the running operation and retries.

## Agent check

`make agent-check` runs this episode's three tasks from [`../shared/agent-check/tasks/ep01.yaml`](../shared/agent-check/tasks/ep01.yaml) under three conditions (model alone, plus the Kubernetes 1.37 context file, plus a repair loop), 10 runs each, with a server-side dry-run against the Rapid cluster:

- a native sidecar for a log shipper (`restartPolicy: Always` on an init container)
- model weights from an OCI image volume
- untrusted code in a user namespace (`hostUsers: false`)

```bash
make -C .. agent-venv                       # once
gcloud auth application-default login       # once
make agent-check AGENT_CHECK_ARGS=--require-all-checks   # needs the Rapid cluster up
```

`make agent-check FAKE_MODEL=1` runs the pipeline offline with canned model replies. See [docs/agent-check.md](../docs/agent-check.md).

## Troubleshooting

- `census knobs` reads `/configz` and `/metrics` through the node proxy. Errors for a pool go to `results/knobs.err`.
- The full text of each failed demo, with the Pod's recent events, is in `results/five-things-errors.log`.
- On Autopilot, the image volume demo is rejected at admission: Autopilot's allowed volume types don't include `image`.
- On Autopilot, the resize demo is rejected at admission because the resized Pod's memory-to-CPU request ratio falls outside Autopilot's range. Autopilot raises the memory request when it creates the Pod, and the demo's patch changes only CPU. A patch that raises memory along with CPU (for example 500m CPU with 1Gi memory) is applied in place.
- On Autopilot, the user namespaces demo Pod stays in ContainerCreating: its sandbox fails to mount `/proc` (permission denied). In our runs the same happened on a Standard node pool with Image streaming turned on, and the Pod ran on Standard node pools without it. Autopilot uses Image streaming automatically.
- Image volumes and user namespaces depend on the node's container runtime and kernel. `results/env.json` records both for each node.
- The swap node pool needs GKE 1.34.1-gke.1341000 or later on the Rapid cluster, and only Burstable Pods can use swap.
