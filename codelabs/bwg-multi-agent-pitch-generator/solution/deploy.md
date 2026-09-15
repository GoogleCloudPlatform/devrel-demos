## Deploy

Export the environment first. `setenv.sh` derives everything from `PROJECT_ID` and `REGION`:

```bash
export PROJECT_ID="your-qwiklabs-project-id"
export REGION="your-lab-region"
source ./setenv.sh
```

> Create a Google Cloud Storage bucket `$PROJECT_ID-bwg` using `gcloud storage buckets create gs://$PROJECT_ID-bwg --uniform-bucket-level-access --location=$REGION --project=$PROJECT_ID` command.

Deploy `visual-director` agent

```bash
pushd visual-director
agents-cli deploy \
  --service-name visual-director \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $GOOGLE_CLOUD_REGION \
  --no-confirm-project \
  --update-env-vars "LOGS_BUCKET_NAME=$LOGS_BUCKET_NAME,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION"
popd
```

Deploy `pitch-generator` workflow and assign cloud run invoker on the account

```bash
pushd pitch-generator
VISUAL_DIRECTOR_URL=$(gcloud run services list --region $GOOGLE_CLOUD_REGION --project $GOOGLE_CLOUD_PROJECT \
  --flatten='spec.template.spec.containers[0].env' \
  --filter='metadata.name=visual-director AND spec.template.spec.containers[0].env.name=APP_URL' \
  --format='value(spec.template.spec.containers[0].env.value)')
agents-cli deploy \
  --service-name pitch-generator \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $GOOGLE_CLOUD_REGION \
  --no-confirm-project \
  --update-env-vars "VISUAL_DIRECTOR_URL=$VISUAL_DIRECTOR_URL,LOGS_BUCKET_NAME=$LOGS_BUCKET_NAME,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION"

SA=$(gcloud run services describe pitch-generator --region $GOOGLE_CLOUD_REGION \
  --format='value(spec.template.spec.serviceAccountName)' --project $GOOGLE_CLOUD_PROJECT)
gcloud run services add-iam-policy-binding visual-director --region $GOOGLE_CLOUD_REGION \
  --member="serviceAccount:$SA" --role=roles/run.invoker --project $GOOGLE_CLOUD_PROJECT
popd
```

## Call the agent

```bash
pushd pitch-generator
source .env
uv run python call_agent.py "astronaut drinking espresso on mars" --save-image ./mars.jpg
popd
```