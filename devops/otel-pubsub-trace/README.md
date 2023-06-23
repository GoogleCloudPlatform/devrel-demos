# Create a trace through Cloud Pub/Sub

This demo shows the minumum example of how to propagate trace via Cloud Pub/Sub on GKE.

## Pre-requisites

* `gcloud` command
* `skaffold` command
* `kubectl` command
* Google Cloud project enabled with:
  * Google Kubernetes Engine
  * Artifact Registry
  * Cloud Build
  * Cloud Trace
  * Cloud Pub/Sub

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
* `cloudbuild.googleapis.com`
* `cloudtrace.googleapis.com`
* `pubsub.googleapis.com`

### Create Pub/Sub topic and subscriber

Because this demo application contains publisher and subscriber of Cloud Pub/Sub,
you need to set up a Pub/Sub topic and its subscriber.

```console
gcloud pubsub topics create otel-pubsub-topic
gcloud pubsub subscriptions create --topic otel-pubsub-topic otel-pubsub-topic-sub
```

### Create service account to use

Because this demo is intended to be a Kubernetes cluster and you need to have a service acccount
linked to workload identity that has permissions for the following roles.

```console
PROJECT_ID=<your-gcp-project-id>
GSA_NAME=<your-gsa>
GSA_EMAIL=${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${GSA_EMAIL}" \
  --role roles/cloudtrace.agent

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${GSA_EMAIL}" \
  --role roles/pubsub.publisher

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${GSA_EMAIL}" \
  --role roles/pubsub.subscriber
```

### Create GKE cluster

Now you have a service account for this demo, create a GKE cluster as you wish.
Please be sure to specify the service account that you just created.

```console
gcloud container clusters create-auto demo-cluster \
  --region=asia-east1 \
  --service-account=${GSA_EMAIL}
```

### Bind workload identity

Then you need to bind workload identity to the service account.

```console
PROJECT_ID=<your-gcp-project-id>
GSA_NAME=<your-gsa>
GSA_EMAIL=${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

gcloud iam service-accounts add-iam-policy-binding ${GSA_EMAIL} \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/default]"

kubectl annotate serviceaccount default \
  iam.gke.io/gcp-service-account=${GSA_EMAIL}
```

### Set up conatiner registry

To use `skaffold`, you need to prepare a container registry, and set it as the default repository.

```console
gcloud artifacts repositories create test-registry \
  --repository-format=docker \
  --location=asia-east1

skaffold config set default-repo asia-east1-docker.pkg.dev/${PROJECT_ID}/test-registry
```

### Run skaffold and deploy

Finally, it's time to deploy the demo on the GKE cluster. Run `skaffold run`. You should see the all build logs from Cloud Build and then see the message that `skaffold` deployed the demo.

```console
$ skaffold run
Generating tags...
 - publisher -> asia-east1-docker.pkg.dev/otel-pubsub-demo/demo-container/publisher:eae9bcb-dirty
 - subscriber -> asia-east1-docker.pkg.dev/otel-pubsub-demo/demo-container/subscriber:eae9bcb-dirty
Checking cache...
 - publisher: Not found. Building
 - subscriber: Found Remotely
Starting build...
Building [publisher]...
Target platforms: [linux/amd64]
Pushing code to gs://otel-pubsub-demo_cloudbuild/source/otel-pubsub-demo-f4aeacbf-a6b3-4728-ad39-129d107f476f.tar.gz
Logs are available at
https://storage.cloud.google.com/otel-pubsub-demo_cloudbuild/log-767c9b2e-9d02-4a1f-8f6d-15db95312c6f.txt
starting build "767c9b2e-9d02-4a1f-8f6d-15db95312c6f"

FETCHSOURCE
Fetching storage object: gs://otel-pubsub-demo_cloudbuild/source/otel-pubsub-demo-f4aeacbf-a6b3-4728-ad39-129d107f476f.tar.gz#1687499998692430
Copying gs://otel-pubsub-demo_cloudbuild/source/otel-pubsub-demo-f4aeacbf-a6b3-4728-ad39-129d107f476f.tar.gz#1687499998692430...
/ [1 files][ 10.0 KiB/ 10.0 KiB]
Operation completed over 1 objects/10.0 KiB.
BUILD
...(omit)...
DONE
Build [publisher] succeeded
Starting test...
...(omit)...
 - deployment/subscriber is ready. [1/2 deployment(s) still pending]
 - deployment/publisher is ready.
Deployments stabilized in 8.691 seconds
You can also run [skaffold run --tail] to get the logs
```

Then you can check the external IP address for the entrypoint:

```console
$ kubectl describe services frontend-external | grep "Ingress"
LoadBalancer Ingress:     104.199.135.40
```

### Publish a message via the publisher service

The endpoint path to generate and publish a massage to Pub/Sub is `/hello`.
Run `curl` to access the endpoint. If the message is successfully generated
and published to the Pub/Sub topic, you'll see `hello` as a response.

```console
$ curl -X GET http://104.199.135.40/hello
hello
```

### Waterfall chart on Cloud Trace

Access to the [Trace explorer](https://console.cloud.google.com/traces/list), then you should
find a trace.

![](./static/waterfall.png)

As you see, the trace information is propagated through the Pub/Sub and the spans from
publisher and subscriber, which runs independently as Kubernetes pods, are linked to
each other.
