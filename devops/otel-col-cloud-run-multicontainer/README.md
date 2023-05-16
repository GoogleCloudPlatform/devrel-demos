## OpenTelemetry sidecar on Cloud Run multi-containers support

This is a sample project that runs OpenTelemetry Collector as a sidecar for an app on Cloud Run multi-containers.

**NOTE: this sample runs always-on container on Cloud Run so that the Collector keep running during the demo. Be sure to shutdown the service after you try it.**

## How to try

1. Create a Google Cloud project with the following services enabled

   * Cloud Build
   * Artifact Registry
   * Cloud Run

2. [Prepare a container registry on Artifact Registry](https://cloud.google.com/artifact-registry/docs/repositories/create-repos)

   * note the registry name (eg. `asia-east1.docker.pkg.dev/sample-project/test-registry`)

3. Replace the registry name in `multicontainers.yaml`.

4. Run the following command to trigger a Cloud Build job.

   * `gcloud builds submit . --config=cloudbuild.yaml --substitutions=_REGISTRY=<registry name>`

5. The default setting doesn't allow unauthorized access. You may want to run the following command to enable unauthorized access.

   * `gcloud run services set-iam-policy otel-sidecar-challenge policy.yaml --region asia-east1`

6. Confirm "Trace List" on Cloud Trace and see those traces are captured.

## Clean up

After you run the demo, be sure to delete the Cloud Run service, so that you won't be charged unexpectedly.

`gcloud run services delete otel-sidecar-challenge --region asia-east1 --quiet`
