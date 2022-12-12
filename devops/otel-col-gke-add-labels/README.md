# Add labels to telemetry using OpenTelemetry Collector processor

This demo shows the minimum example of how to embed Kubernetes cluster wide telemetry using OpenTelemetry Collector's processor.

## Pre-requisites

* `gcloud` command
* `skaffold` command
* `kubectl` command
* Google Cloud project account enabled with:
  * Google Kubernetes Engine
  * Container Registry or Artifact Registry
  * Cloud Build
  * Cloud Trace

You can set up `skaffold` and `kubectl` via `gcloud` command.

```
gcloud components install skaffold kubectl
```

## How to run

```
./create-cluster.sh
skaffold config set default-repo <path to container registry>
```

For example, if you are using Container Registry, you can set up `skaffold` like:

```
skaffold config set default-repo gcr.io/$(gcloud config get-value project)
```

Then run the project:

```
skaffold run
```
