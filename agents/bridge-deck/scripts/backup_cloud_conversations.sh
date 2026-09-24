#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Bridge Deck: Cloud Conversation Backup Script
# ==============================================================================
# Safely pulls authoritative conversation and tenant data from Google Cloud GCS
# into a local timestamped snapshot under data/backups/ (excluded from git/docker).
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

if [[ -z "${GCS_DATA_BUCKET}" ]]; then
    echo "❌ ERROR: GCS_DATA_BUCKET must be set or defined in deploy.env"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${ROOT_DIR}/data/backups/snapshot_${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

echo "=================================================="
echo " Bridge Deck: Backing up Cloud Conversation Data"
echo "=================================================="
echo "Source Bucket : gs://${GCS_DATA_BUCKET}/tenants/"
echo "Target Backup : ${BACKUP_DIR}/tenants/"
echo "=================================================="

gcloud storage cp -r "gs://${GCS_DATA_BUCKET}/tenants/" "${BACKUP_DIR}/"

echo "✅ Backup successfully downloaded to ${BACKUP_DIR}/tenants/"

FILE_COUNT=$(find "${BACKUP_DIR}" -type f | wc -l | tr -d ' ')
echo "Total files backed up: ${FILE_COUNT}"
