#!/usr/bin/env bash
# /**
#  * @file scripts/deploy.sh
#  * @description Smart Cloud Run deployment script for the Agentic Pitch Generator.
#  *
#  * Why: Dynamically inspects the learner's workspace (`pitch_generator/agent.py`) to
#  * determine which services have been built. In the starter state, it deploys only
#  * `pitch-generator`. Once the learner adds the Visual Director specialist / remote A2A
#  * service in Module 1, it automatically deploys `visual-director` first, resolves its
#  * URL, and then deploys `pitch-generator` with `VISUAL_DIRECTOR_URL` wired.
#  *
#  * @param --dry-run Optional flag to print deployment commands without executing live cloud builds.
#  * @param --service Optional target service override (`auto`, `pitch-generator`, `visual-director`, or `all`).
#  * @return 0 on successful deployment or dry-run validation.
#  */

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DRY_RUN=0
TARGET_SERVICE="auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --service)
      TARGET_SERVICE="${2:-auto}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "${PITCH_OFFLINE_MODE:-0}" == "1" ]]; then
  DRY_RUN=1
fi

# /**
#  * Inspects pitch_generator/agent.py via Python AST to check whether the learner has
#  * defined the Visual Director service (`visual_director`, `remote_visual_director`,
#  * `generate_key_visual`, or `build_a2a_visual_director_app`).
#  *
#  * Why: Allows `./scripts/deploy.sh` to work out of the box for the starter app
#  * (deploying only `pitch-generator`) and automatically include `visual-director`
#  * once the learner builds it during the lab.
#  *
#  * @return 0 (true) if Visual Director symbols exist in pitch_generator/agent.py, 1 (false) otherwise.
#  */
has_visual_director_built() {
  local agent_file="${APP_ROOT}/pitch_generator/agent.py"
  if [[ ! -f "${agent_file}" ]]; then
    return 1
  fi
  python3 - "${agent_file}" <<'PYEOF'
import ast
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=sys.argv[1])
except Exception:
    sys.exit(1)

defined = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        defined.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                defined.add(t.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        defined.add(node.target.id)

vd_markers = {
    "visual_director",
    "remote_visual_director",
    "generate_key_visual",
    "build_a2a_visual_director_app",
    "create_remote_visual_director_agent",
}
sys.exit(0 if (defined & vd_markers) else 1)
PYEOF
}

# /**
#  * Deploys a service to Cloud Run using agents-cli when available or gcloud run deploy as fallback.
#  *
#  * Why: Preserves compatibility with the agents-cli workflow taught in the lab while allowing
#  * standard Cloud Build / Cloud Run container deployments from the same repository root.
#  *
#  * @param $1 Service name to deploy.
#  * @return 0 on success.
#  */
deploy_cloud_run_service() {
  local service_name="$1"
  local env_vars="LOGS_BUCKET_NAME=${LOGS_BUCKET_NAME},GOOGLE_GENAI_USE_ENTERPRISE=TRUE,GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION},MEMORY_BANK_ID=${MEMORY_BANK_ID},FLASH_MODEL=${FLASH_MODEL},IMAGE_MODEL=${IMAGE_MODEL},VISUAL_DIRECTOR_URL=${VISUAL_DIRECTOR_URL}"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] Deploying ${service_name} to Cloud Run in ${GOOGLE_CLOUD_PROJECT} (${GOOGLE_CLOUD_REGION}) with env: ${env_vars}"
    return 0
  fi

  if command -v agents-cli >/dev/null 2>&1; then
    agents-cli deploy \
      --service-name "${service_name}" \
      --project "${GOOGLE_CLOUD_PROJECT}" \
      --region "${GOOGLE_CLOUD_REGION}" \
      --no-confirm-project \
      --update-env-vars "${env_vars}"
  else
    gcloud run deploy "${service_name}" \
      --source "${APP_ROOT}" \
      --project "${GOOGLE_CLOUD_PROJECT}" \
      --region "${GOOGLE_CLOUD_REGION}" \
      --set-env-vars "${env_vars}" \
      --quiet
  fi
}

# /**
#  * Main entrypoint coordinating environment loading, dynamic workspace detection, and deployment order.
#  *
#  * @return 0 on completion.
#  */
main() {
  # shellcheck disable=SC1091
  PITCH_OFFLINE_MODE="${DRY_RUN}" source "${APP_ROOT}/setenv.sh"

  local deploy_vd=0
  local deploy_pg=0

  case "${TARGET_SERVICE}" in
    visual-director)
      deploy_vd=1
      ;;
    pitch-generator)
      deploy_pg=1
      ;;
    all)
      deploy_vd=1
      deploy_pg=1
      ;;
    auto|*)
      deploy_pg=1
      if has_visual_director_built; then
        echo "[deploy] Detected Visual Director in pitch_generator/agent.py — deploying both visual-director and pitch-generator."
        deploy_vd=1
      else
        echo "[deploy] Starter workflow detected (no Visual Director in pitch_generator/agent.py yet) — deploying pitch-generator only."
      fi
      ;;
  esac

  if [[ "${deploy_vd}" -eq 1 ]]; then
    deploy_cloud_run_service "visual-director"
    if [[ "${DRY_RUN}" -eq 0 ]] && command -v gcloud >/dev/null 2>&1; then
      local resolved_vd_url
      resolved_vd_url="$(gcloud run services describe visual-director --project "${GOOGLE_CLOUD_PROJECT}" --region "${GOOGLE_CLOUD_REGION}" --format='value(status.url)' 2>/dev/null || true)"
      if [[ -n "${resolved_vd_url}" ]]; then
        export VISUAL_DIRECTOR_URL="${resolved_vd_url}"
      fi
    fi
  fi

  if [[ "${deploy_pg}" -eq 1 ]]; then
    deploy_cloud_run_service "pitch-generator"
  fi

  echo "Deployment complete for target: ${TARGET_SERVICE}"
}

main "$@"
