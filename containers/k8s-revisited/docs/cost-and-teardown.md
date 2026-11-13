# Cost and teardown

## What an episode creates

Each episode's runbook lists the clusters and node pools it creates and roughly how long they need to stay up. For example, Ep1 creates three small clusters (Rapid and Stable Standard clusters, plus an Autopilot cluster) and a small swap-enabled node pool, for about an hour.

## Guardrails

- Use a dedicated project with a monthly budget and alerts at 50%, 90% and 100%.
- Resources get the labels `series=k8s-revisited,episode=epNN,ttl=<duration>`.
- Standard clusters are zonal, in the one region set in `shared/infra/.env`. Autopilot clusters are regional.
- Delete clusters on the day you create them, or scale node pools to 0 between sessions.

## Teardown

```bash
make epNN-down                     # what one episode created
./shared/infra/reaper.sh --check   # lists anything still labeled series=k8s-revisited; exits 1 if found
./shared/infra/reaper.sh --delete  # deletes it (asks first)
```
