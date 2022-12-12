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

Also you can enable the APIs via `gcloud` command:

```
gcloud services enable <service name>
```

The required services for this demo are:

* `container.googleapis.com`
* `artifactregistry.googleapis.com`
* `containerregistry.googleapis.com`
* `cloudbuild.googleapis.com`
* `cloudtrace.googleapis.com`

## How to run

```
./create-cluster.sh <cluster name>
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

This command sends project files to your Cloud Build environment, and remotely build and deploy the project to GKE.

## How to confirm the result

Check the Trace List page in Cloud Trace menu. Then you will start to see the dots in the trace distribution window.

Pick one dots from the trace list, and find the labels such as `k8s.cluster.name`, `cloud.region` and so on, in the "Labels" section at bottom right of the page. The labels added by the processor are:

* `cloud.account.id`
* `cloud.platform`
* `cloud.provider`
* `cloud.region`
* `host.id`
* `host.name`
* `k8s.cluster.name`

## Clean up

Once you try and understand how it works, run the following commands to delete the resources you used so that you won't be charged for unnecessary workloads.

```
skaffold delete
```

Also, you can turn down the Kubernetes cluster:

```
gcloud container cluster delete <cluster name>
```

If you prepared a new project dedicated for this demo, you can delete it.

```
gcloud projects delete <project ID or number>
```
