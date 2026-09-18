#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Bridge Deck: Standalone Cloud Tenant Seeding Script
# ==============================================================================
# Performs a one-time initial seed of tenant data to Google Cloud Storage.
# SAFETY INVARIANT: Refuses to run unless the destination prefix in GCS is
# PROVABLY empty (0 objects). Never runs automatically during deployments.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f "deploy.env" ]]; then
    # shellcheck disable=SC1091
    source deploy.env
fi

GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
GCS_DATA_BUCKET="${GCS_DATA_BUCKET:-${GOOGLE_CLOUD_PROJECT}-bridge-deck-data}"
BRIDGE_DEFAULT_TENANT="${BRIDGE_DEFAULT_TENANT:-}"

if [[ -z "${GOOGLE_CLOUD_PROJECT}" || -z "${BRIDGE_DEFAULT_TENANT}" ]]; then
    echo "❌ ERROR: GOOGLE_CLOUD_PROJECT and BRIDGE_DEFAULT_TENANT must be set in deploy.env"
    exit 1
fi

DEST_PREFIX="gs://${GCS_DATA_BUCKET}/tenants/${BRIDGE_DEFAULT_TENANT}/"
LOCAL_SRC="data/tenants/${BRIDGE_DEFAULT_TENANT}/"

echo "=================================================="
echo " Bridge Deck: Standalone Tenant Seed"
echo "=================================================="
echo "Tenant      : ${BRIDGE_DEFAULT_TENANT}"
echo "Local Source: ${LOCAL_SRC}"
echo "Destination : ${DEST_PREFIX}"
echo "=================================================="

if [[ ! -d "${LOCAL_SRC}" ]]; then
    echo "❌ ERROR: Local source directory ${LOCAL_SRC} does not exist."
    exit 1
fi

# Verify destination prefix is provably empty
echo "Verifying remote destination is provably empty..."
if ! gcloud storage buckets describe "gs://${GCS_DATA_BUCKET}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
    echo "❌ ERROR: Cannot access bucket gs://${GCS_DATA_BUCKET}. Check credentials and project permissions."
    exit 1
fi

LS_STATUS=0
LS_OUTPUT=$(gcloud storage ls "${DEST_PREFIX}" --project="${GOOGLE_CLOUD_PROJECT}" 2>&1) || LS_STATUS=$?

if [[ ${LS_STATUS} -eq 0 ]]; then
    EXISTING_COUNT=$(echo "${LS_OUTPUT}" | grep -v '^[[:space:]]*$' | wc -l | tr -d ' ')
    if [[ "${EXISTING_COUNT}" -gt 0 ]]; then
        echo "❌ REFUSAL: Destination ${DEST_PREFIX} already contains ${EXISTING_COUNT} object(s)."
        echo "👉 Google Cloud is the authoritative system of record. Seeding over existing data is prohibited."
        exit 1
    fi
elif echo "${LS_OUTPUT}" | grep -q "matched no objects"; then
    echo "✅ Destination prefix is provably empty."
else
    echo "❌ ERROR: Failed to inspect destination prefix ${DEST_PREFIX}:"
    echo "${LS_OUTPUT}"
    exit 1
fi
read -r -p "Are you sure you want to seed ${LOCAL_SRC} to ${DEST_PREFIX}? [y/N] " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    echo "Operation cancelled."
    exit 0
fi

gcloud storage cp -r "${LOCAL_SRC}*" "${DEST_PREFIX}"
echo "✅ Initial seeding complete."
