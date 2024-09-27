### INCOMPLETE

PROJECT_ID=<YOUR-PROJECT-ID>
REGION=<YOUR-REGION>
GCAR_REPO=my-repo
APP_NAME=gemini-app

python <<EOF
import yaml

PROJECT_ID="${PROJECT_ID}"
REGION="${REGION}"
REPO="${GCAR_REPO}"
APP_NAME="${APP_NAME}"

with open("service.yaml", "r+") as f:
    y = yaml.safe_load(f)
    y["metadata"]["name"] = APP_NAME
    y["spec"]["template"]["spec"]["containers"][0]["image"] = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO}/{APP_NAME}"
    y["spec"]["template"]["spec"]["containers"][0]["env"][1]["value"] = PROJECT_ID
    y["spec"]["template"]["spec"]["containers"][0]["env"][2]["value"] = REGION
    y["spec"]["template"]["spec"]["containers"][1]["image"] = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO}/otel-collector-metrics"
    f.seek(0)
    yaml.dump(y, f, sort_keys=False)
    f.truncate()
EOF

# Create artifact registry if it doesn't already exist
gcloud artifacts repositories describe ${GCAR_REPO} \
    --location=${REGION} \
    --project=${PROJECT_ID} >/dev/null 2>&1  ||
gcloud artifacts repositories create ${GCAR_REPO} \
    --repository-format=docker \
    --location=${REGION} \
    --project=${PROJECT_ID}

# Create app image
gcloud builds submit \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${GCAR_REPO}/${APP_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID}

# Create collector image
gcloud builds submit collector \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${GCAR_REPO}/otel-collector-metrics \
    --region=${REGION} \
    --project=${PROJECT_ID}

# Create the Cloud Run app
gcloud run services replace service.yaml \
    --region=${REGION} \
    --project=${PROJECT_ID}

# (Optional) Allow unauthenticated calls
# gcloud run services set-iam-policy ${APP_NAME} unauthenticated_policy.yaml \
#     --region=${REGION}
#     --project=${PROJECT_ID}

# Need to also create BigQuery dataset, embeddings, and firestore db