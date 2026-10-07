#!/usr/bin/env bash
# /**
#  * @file scripts/setup.sh
#  * @description Provisions Google Cloud storage and BigQuery analytics prerequisites for Pitch Generator.
#  *
#  * Why: Automates idempotent setup of the artifact Cloud Storage bucket (<PROJECT_ID>-bwg),
#  * BigQuery dataset (bwg), BigQuery Cloud Resource connection (pitch-connection), and
#  * delegated IAM bindings (Storage Object Viewer and Agent Platform User) so learners
#  * and CI environments have consistent infrastructure for Modules 1-4.
#  *
#  * @param --dry-run Optional flag to print planned commands without mutating remote cloud state.
#  * @return 0 on success, non-zero on configuration or command error.
#  */

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DRY_RUN=0

for arg in "$@"; do
  if [[ "${arg}" == "--dry-run" ]]; then
    DRY_RUN=1
  fi
done

if [[ "${PITCH_OFFLINE_MODE:-0}" == "1" ]]; then
  DRY_RUN=1
fi

# /**
#  * Executes or logs a shell command depending on dry-run mode.
#  *
#  * Why: Wrapping external CLI invocations in run_cmd allows offline verification tests
#  * (Constraint R4) to validate the exact setup workflow without mutating live GCP projects.
#  *
#  * @param $@ Command and arguments to execute.
#  * @return 0 on success.
#  */
run_cmd() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] $*"
    return 0
  fi
  "$@"
}

# /**
#  * Creates the Cloud Storage bucket for persisting generated campaign key visuals.
#  *
#  * Why: Uniform bucket-level access simplifies IAM delegation so the BigQuery Cloud
#  * Resource connection service account can read ObjectRef artifacts via a single role binding.
#  *
#  * @return 0 when bucket exists or is created.
#  */
ensure_bucket() {
  echo "Ensuring Cloud Storage bucket gs://${LOGS_BUCKET_NAME} in ${GOOGLE_CLOUD_REGION}..."
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    run_cmd gcloud storage buckets create "gs://${LOGS_BUCKET_NAME}" \
      --project="${GOOGLE_CLOUD_PROJECT}" \
      --location="${GOOGLE_CLOUD_REGION}" \
      --uniform-bucket-level-access
    return 0
  fi
  if ! gcloud storage buckets describe "gs://${LOGS_BUCKET_NAME}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${LOGS_BUCKET_NAME}" \
      --project="${GOOGLE_CLOUD_PROJECT}" \
      --location="${GOOGLE_CLOUD_REGION}" \
      --uniform-bucket-level-access
  fi
}

# /**
#  * Creates the BigQuery dataset (bwg) and Cloud Resource connection (pitch-connection).
#  *
#  * Why: BigQuery needs delegated credentials via a Cloud Resource connection to inspect
#  * Cloud Storage images via OBJ.MAKE_REF / OBJ.FETCH_METADATA and to invoke Gemini models
#  * on Agent Platform via AI.SCORE.
#  *
#  * @return 0 when dataset and connection are ready.
#  */
ensure_bigquery_dataset_and_connection() {
  echo "Ensuring BigQuery dataset bwg and connection pitch-connection..."
  run_cmd bq --location="${GOOGLE_CLOUD_REGION}" mk --dataset \
    --default_table_expiration=0 \
    "${GOOGLE_CLOUD_PROJECT}:bwg" || true

  run_cmd bq mk --connection \
    --location="${GOOGLE_CLOUD_REGION}" \
    --project_id="${GOOGLE_CLOUD_PROJECT}" \
    --connection_type=CLOUD_RESOURCE \
    pitch-connection || true
}

# /**
#  * Grants Storage Object Viewer and Agent Platform User roles to the BigQuery connection SA.
#  *
#  * Why: Newly created BigQuery Cloud Resource connections provision their service account
#  * identity asynchronously; retrying prevents transient IAM binding failures during setup.
#  *
#  * @return 0 once IAM bindings succeed.
#  */
grant_connection_iam() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] Granting roles/storage.objectViewer and roles/aiplatform.user to pitch-connection service account"
    return 0
  fi

  local sa_email=""
  for attempt in 1 2 3 4 5; do
    sa_email="$(bq show --format=json --connection "${GOOGLE_CLOUD_PROJECT}.${GOOGLE_CLOUD_REGION}.pitch-connection" 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('cloudResource', {}).get('serviceAccountId', ''))" || true)"
    if [[ -n "${sa_email}" ]]; then
      break
    fi
    sleep 2
  done

  if [[ -n "${sa_email}" ]]; then
    for role in "roles/storage.objectViewer" "roles/aiplatform.user"; do
      gcloud projects add-iam-policy-binding "${GOOGLE_CLOUD_PROJECT}" \
        --member="serviceAccount:${sa_email}" \
        --role="${role}" \
        --condition=None >/dev/null
    done
  fi
}

# /**
#  * Main entrypoint orchestrating environment initialization, bucket creation, and BigQuery setup.
#  *
#  * @return 0 on completion.
#  */
main() {
  PITCH_OFFLINE_MODE="${DRY_RUN}" source "${APP_ROOT}/setenv.sh"
  ensure_bucket
  ensure_bigquery_dataset_and_connection
  grant_connection_iam
  echo "🎉  🦄 Script execution complete."
}

main "$@"
