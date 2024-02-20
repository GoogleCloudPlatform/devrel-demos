# Trace exemplar with Cloud Trace and Cloud Monitoring using OpenTelemetry

This is a sample project that demonstrates how to send metrics with trace exemplars using OpenTelemetry.

## How to try

1. Create a Google Cloud project with the following services enabled:
    * Cloud Build
    * Artifact Registry
    * Cloud Run
    * Cloud Trace
    * Cloud Monitoring

2. [Prepare a container registry on Artifact Registry](https://cloud.google.com/artifact-registry/docs/repositories/create-repos)
    * Note the registry name (eg. `asia-east1.docker.pkg.dev/sample-project/test-registry`)

3. Replace the registry name in `multicohntainers.yaml`
    * i.e. replace `${YOUR_CONTAINER_REGISTRY_NAME}` with the registry name in step 2.

4. Run the following command to trigger a Cloud Build job
    * `gcloud builds submit . --config=cloudbuild.yaml --substitutions=_REGISTRY=<registry name>`

5. Note that the default Cloud Run service setting doesn't allow unauthorized access
    * Change the service to allow unauthenticated access

6. Run the following command to generate the continuous access:
    * `watch -n 10 curl -X GET https://otel-exemplar-test-xxxxxx.a.run.app/root`
    * Find the right URL to access from Cloud Run metadata
