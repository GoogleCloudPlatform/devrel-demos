# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 

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

export GOOGLE_CREDENTIALS=~/terraform-sa-key.json

echo "Applying Terraform"
terraform init
terraform apply -auto-approve \
    -var project_id=$PROJECT_ID \
    -var github_repo=$GITHUB_REPO

export WIF_PROVIDER=$(terraform output wif_provider)
export SERVICE_ACCOUNT=$(terraform output service_account)

printf "\n\n\e[32mConfiguration complete. \e[0m\n\n"