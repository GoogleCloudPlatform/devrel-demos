# Invoke agent application asynchronously using PubSub

This demo shows how to use [Eventarc][1] to [trigger a Cloud Run service][2] in order to implement asynchronous invocation of an AI agent deployed on Cloud Run.
The AI agent implements a single AI agent application that helps visitors to a fictional Zoo to learn about animals in the Zoo.
The demo uses [ADK][3] to develop agentic applications and follows best security practices to deploy the application in a way that it can be accessed only using Eventarc events.

## How to deploy

### Setup configuration variables

```shell
export LOCATION="us-central1"
export PROJECT_ID="YOUR_PROJECT_ID"
gcloud config set project "${PROJECT_ID}"
```

### Enable necessary APIs

```shell
gcloud services enable \
    aiplatform.googleapis.com \
    eventarc.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    pubsub.googleapis.com
```

### Create PubSub topics

1. Create PubSub topic for Eventarc trigger

   ```shell
   gcloud pubsub topics create invoke_agent
   ```

1. Create PubSub topic for agent's responses

   ```shell
   gcloud pubsub topics create agent_responses
   ```

1. Create PubSub subscription for agent's responses so posted messages aren't lost

   ```shell
   gcloud pubsub subscriptions create agent_responses \
       --topic=agent_responses
   ```

1. Keep full-formatted ids of the topics as environment variables

   ```shell
   export INVOKE_TOPIC_ID=$(gcloud pubsub topics describe invoke_agent --format="value(name)")
   export RESPONSE_TOPIC_ID=$(gcloud pubsub topics describe agent_responses --format="value(name)")
   ```

### Deploy the agent to Cloud Run

1. Create dedicated service account

   ```shell
   gcloud iam service-accounts create zookeeper-cloudrun-sa
   export ZOOKEEPER_SA="zookeeper-cloudrun-sa@${PROJECT_ID}.iam.gserviceaccount.com"
   ```

1. Grant permissions to the service account to write logs, traces and use hosted LLM models

   ```shell
   gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
       --member="serviceAccount:${ZOOKEEPER_SA}" \
       --role="roles/logging.logWriter" \
       --condition=None
   gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
       --member="serviceAccount:${ZOOKEEPER_SA}" \
       --role="roles/cloudtrace.agent" \
       --condition=None
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${ZOOKEEPER_SA}" \
        --role="roles/aiplatform.user" \
        --condition=None
    ```

1. Grant permissions to the service account to post to the agent responses topic

    ```shell
    gcloud pubsub topics add-iam-policy-binding agent_responses \
        --member="serviceAccount:${ZOOKEEPER_SA}" \
        --role="roles/pubsub.publisher" \
        --condition=None
    ```

1. Deploy Cloud Run service from the source

   ```shell
   gcloud run deploy zookeeper-agent \
       --region="${LOCATION}" \
       --source="." \
       --no-allow-unauthenticated \
       --service-account="${ZOOKEEPER_SA}" \
       --set-env-vars="REPLY_TOPIC_ID=${RESPONSE_TOPIC_ID}"
   ```

Read more about the above command in the [instructions](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service#deploy).
The designated service account is granted permissions to write logs and traces (to support ADK logging and tracing) and to post responses to the designated PubSub topic.

### Configure Eventarc trigger

1. Create dedicated service account

   ```shell
   gcloud iam service-accounts create zookeeper-trigger-sa
   export TRIGER_SA="zookeeper-trigger-sa@${PROJECT_ID}.iam.gserviceaccount.com"
   ```

1. Create event

   ```shell
   gcloud eventarc triggers create invoke-agent \
       --location="${LOCATION}" \
       --destination-run-service="zookeeper-agent" \
       --destination-run-path="/zookeeper" \
       --destination-run-region="${LOCATION}" \
       --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
       --transport-topic="${INVOKE_TOPIC_ID}" \
       --service-account="${TRIGER_SA}"
   ```

1. Grant permissions to the service account to invoke the agent deployed on Cloud Run

   ```shell
   gcloud run services add-iam-policy-binding zookeeper-agent \
       --region="${LOCATION}" \
       --member="serviceAccount:${TRIGER_SA}" \
       --role="roles/run.invoker"

   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   gcloud iam service-accounts add-iam-policy-binding "${TRIGGER_SA}" \
       --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
       --role="roles/iam.serviceAccountTokenCreator"
   ```

Read more about the above command in the [instructions](https://docs.cloud.google.com/run/docs/triggering/pubsub-triggers#trigger-services).
The designated service account is granted permissions to invoke the agent in Cloud Run.
The Google-managed service account created automatically when the Eventarc trigger for PubSub was created is granted permissions to "impersonate" or generate tokens for the trigger's service account.

## How to interact with the Zookeeper agent

To invoke the agent push a message with the following format to the topic "invoke_agent".

Format:

```json
{
    "user_id": "identity_of_invoker", // if omitted the "pubsub" identity will be used
    "prompt": "place your request to the agent here"
}
```

Use the following command to send the request:

```shell
gcloud pubsub topics publish invoke_agent \
    --message='{"user_id":"your_user_id", "prompt":"How many animals you have in the zoo. Show the list."}'
```

The response will be posted to the topic "agent_responses".
Use the following command to pull the messages posted to the topic:

```shell
gcloud pubsub subscriptions pull agent_responses --auto-ack
```

## Troubleshooting

Review the agent's logs to identify failure or reported error:

```shell
gcloud logging read \
  'resource.type = "cloud_run_revision" AND \
   resource.labels.service_name = "zookeeper-agent" AND \
   resource.labels.location = "us-central1"'
```

Change the "location" value if you deploy to a region other than `us-central1`.

## Clean up

TBD

## Additional materials

* Use [] codelab to deploy and run the demo using guided step-by-step tutorial
* Learn how to [triggering Cloud Run service with PubSub][2]
* Learn how to [deploy a customizable ADK Runner][4]

[1]: https://docs.cloud.google.com/eventarc/docs
[2]: https://docs.cloud.google.com/run/docs/triggering/pubsub-triggers
[3]: https://google.github.io/adk-docs/
[4]: https://google.github.io/adk-docs/observability/cloud-trace/#from-customized-agent-runner

<https://codelabs.developers.google.com/codelabs/cloud-run-events#0>
