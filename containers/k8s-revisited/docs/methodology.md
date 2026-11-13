# Measurement methodology

## Scope

Only what we can measure on infrastructure we run, which is GKE. No vendor numbers. No competitor products.

## Record the environment with every run

- GKE version and release channel, Standard or Autopilot, zone or region
- Machine type, node image, kernel, container runtime version
- The node system config file, if a node pool uses one
- gVisor version, where a sandbox runtime is involved
- Feature gates (attach the `census` output for the cluster)

`make env` (or `python3 -m k8s_revisited_bench.envinfo --out results/env.json`) captures most of this.

## Timing

Kubernetes object timestamps only have 1-second resolution. For anything sub-second, use client-side monotonic timers on watch events (`k8s_revisited_bench.k8swatch`).

## Load and statistics

- Generate load open-loop, so coordinated omission doesn't distort latency.
- Warm up first, and run at least 30 trials per condition.
- Record p50, p95 and p99, plus p99.9 for latency, in the raw CSVs.

## Coding-agent runs

- Infrastructure timing replays recorded model turns, so model latency doesn't mix with infrastructure latency.
- Agent checks use one pinned model version, a pinned temperature and a recorded date. Each task and condition runs at least 10 times.

## Results and the posts

Raw results stay in each episode's `results/` folder, which is gitignored. The articles describe what the runs showed in words ("lower than", "higher than", "kept running", "was rejected") and keep only setup numbers such as versions, machine types and task counts. Rerun an episode to get your own numbers.
