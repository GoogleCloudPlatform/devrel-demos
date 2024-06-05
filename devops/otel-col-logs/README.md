# Log forwarding with OpenTelemetry Collector

This demo shows the minimum example of log forwarding using OpenTelemetry Collector from a GKE pod.

## Pre-requisites

* `gcloud` command
* `skaffold` command
* `kubectl` command
* Google Cloud project account enabled with:
  * Google Kubernetes Engine
  * Artifact Registry
  * Cloud Build
  * Cloud Logging

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
* `logging.googleapis.com`

## How to run

```
./create-cluster.sh
skaffold config set default-repo <path to container registry>
```

For example, if you are using Container Registry, you can set up `skaffold` like:

```
skaffold config set default-repo asia-east1-docker.pkg.dev/$(gcloud config get-value project)/<repo name>
```

To confirm the registry URL, you should find it on Cloud Console or by the following command:

```
gcloud artifacts repositories describe <repo name>
```

After setting up default-repo of `skaffold`, run the project:

```
skaffold run
```

This command sends project files to your Cloud Build environment, and remotely build and deploy the project to GKE.

## How to confirm the result

First, you need to generate logs. Find the external IP of the cluster and access the IP in HTTP GET:

```
$ kubectl get services --namespace otel-collector-log-demo
NAME               TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)        AGE
log-app-external   LoadBalancer   10.3.251.149   35.201.245.242   80:32229/TCP   4m58s
otel-collector     ClusterIP      10.3.245.40    <none>           4317/TCP       4m58s

$ curl 35.201.245.242
counter: 46
```

Check the Logs Explorer in Cloud Logging menu. The log name of logs via OpenTelemetry is labeled as `projects/yoshifumi-demo/logs/opentelemetry.io%2Fcollector-exported-log`, so you can filter the logs with the following Log query (please replace `PROJECT_NAME` with your project ID):

```
logName="projects/PROJECT_NAME/logs/opentelemetry.io%2Fcollector-exported-log"
```

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
