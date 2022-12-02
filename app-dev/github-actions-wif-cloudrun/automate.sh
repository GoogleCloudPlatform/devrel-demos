echo "Configuring Workload Identity Federation..."
echo "  Google Cloud Project ID:  ${PROJECT_ID}"
echo "  Google Cloud Region:      ${REGION}"
echo "  Cloud Run Service:        ${SERVICE}"
echo "  GitHub Repo:              ${GITHUB_REPO}"

echo "Creating service account"
gcloud iam service-accounts create terraform-sa \
    --display-name "Terraform Service Account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member serviceAccount:terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/owner
gcloud iam service-accounts keys create ~/terraform-sa-key.json \
    --iam-account terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com
export GOOGLE_APPLICATION_CREDENTIALS=~/terraform-sa-key.json

echo "\nApplying Terraform"
terraform init
terraform apply -auto-approve \
    -var project_id=$PROJECT_ID \
    -var github_repo=$GITHUB_REPO

export WIF_PROVIDER=$(terraform output wif_provider)
export SERVICE_ACCOUNT=$(terraform output service_account)

echo "Configuration complete."