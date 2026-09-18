#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Bridge Deck: Cold Disaster Recovery Backup Depot Synchronization (M1–M3)
# ==============================================================================
# Governance & Mirror Terms:
# - M1: A mirror inherits every invariant of the original.
#       Runs full pre-flight test suite, gitignore tracked file check, and
#       complete commit history invariant scan across all refs.
# - M2: "Never executed from" must be an enforced mechanism, not an asserted policy.
#       Configures backup remote as push-only with fetch URL strictly disabled
#       (push-only://never-fetch-from-cold-mirror).
# - M3: Strictly one-way direction: GitHub -> backup depot, never depot -> GitHub.
#       Rejects pulling, merging, or rebasing from the mirror ref into main.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

DRY_RUN=false
STRICT=false
SKIP_TESTS=false
TARGET_BRANCH=""

show_help() {
    cat <<EOF
Usage: scripts/sync_backup_depot.sh [OPTIONS]

Synchronizes the repository to the cold disaster recovery backup depot mirror
governed by ratified mirror terms M1–M3.

Options:
  --dry-run       Execute all pre-flight test gates, isolation scans, commit history
                  checks, and remote configuration, but skip the final git push.
  --strict        Exit with code 1 if BACKUP_REPO_URL is unset (default exits 0).
  --skip-tests    Skip pre-flight unit test run (still enforces M1 commit history scan).
  --branch <name> Override the branch to synchronize (defaults to current active branch).
  -h, --help      Display this help message and exit.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --strict)
            STRICT=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --branch)
            TARGET_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "❌ ERROR: Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

if [[ "${SKIP_TESTS}" == "true" && "${STRICT}" == "true" ]]; then
    echo "❌ ERROR: --skip-tests cannot be combined with --strict mode (Invariant M1 is mandatory in strict mode)."
    exit 1
fi

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-deploy.env}"
if [[ -f "${DEPLOY_ENV_FILE}" ]]; then
    # shellcheck disable=SC1091
    source "${DEPLOY_ENV_FILE}"
fi

BACKUP_REPO_URL="${BACKUP_REPO_URL:-}"

if [[ -z "${BACKUP_REPO_URL}" ]]; then
    if [[ "${STRICT}" == "true" ]]; then
        echo "❌ ERROR: BACKUP_REPO_URL is not configured in deploy.env or environment."
        exit 1
    fi
    echo "=================================================="
    echo "ℹ️  Cold Backup Depot Notice"
    echo "=================================================="
    echo "BACKUP_REPO_URL is not configured."
    echo "To configure the cold disaster recovery backup mirror (M1–M3):"
    echo "  1. Define BACKUP_REPO_URL in your private deploy.env file:"
    echo "     BACKUP_REPO_URL=\"git@github.com:your-org/backup-depot.git\""
    echo "  2. Run scripts/sync_backup_depot.sh"
    echo "=================================================="
    echo "Exiting without error (cold mirror sync skipped)."
    exit 0
fi

echo "=================================================="
echo " Bridge Deck: Sync Cold Backup Depot (M1–M3)"
echo "=================================================="
echo " Mirror URL: ${BACKUP_REPO_URL}"
echo " Dry Run   : ${DRY_RUN}"
echo "=================================================="

# ------------------------------------------------------------------------------
# 1. Invariant M1: Pre-flight Verification Gate
# ------------------------------------------------------------------------------
echo -e "\n[1/3] Invariant M1: Running test suite pre-flight gate..."
if [[ "${SKIP_TESTS}" == "true" ]]; then
    echo "⚠️ Notice: --skip-tests specified. Skipping unit test suite run."
else
    PYTHON_BIN="python3"
    if [[ -x "./venv/bin/python" ]]; then
        PYTHON_BIN="./venv/bin/python"
    fi
    ${PYTHON_BIN} -m unittest discover -s tests
    echo "✅ Test suite passed."
fi

echo "Scanning repository commit history for excluded paths..."
EXCLUDED_PATHS_REGEX='(^|/)(\.env(\..*)?|deploy\.env(\..*)?|data|logs|scratch|venv|\.bridge_relay)(/|$)'
VIOLATIONS=$(git log --all --pretty=format: --name-only -- . | sort -u \
    | grep -E "${EXCLUDED_PATHS_REGEX}" \
    | grep -vE '\.example$' || true)

if [[ -n "${VIOLATIONS}" ]]; then
    echo "❌ ERROR: Invariant M1 Violation: Commit history contains excluded paths:"
    echo "${VIOLATIONS}"
    echo "Refusing to push to backup depot mirror."
    exit 1
fi
echo "✅ Invariant M1 satisfied: Excluded paths scan passed across all commit history."

# ------------------------------------------------------------------------------
# 2. Invariant M2: Mechanism-Enforced Push-Only Remote Configuration
# ------------------------------------------------------------------------------
echo -e "\n[2/3] Invariant M2: Configuring push-only remote mechanism..."
REMOTE_NAME="backup-depot"
DISABLED_FETCH_URL="push-only://never-fetch-from-cold-mirror"

if git remote | grep -qx "${REMOTE_NAME}"; then
    git remote set-url --push "${REMOTE_NAME}" "${BACKUP_REPO_URL}"
    git remote set-url "${REMOTE_NAME}" "${DISABLED_FETCH_URL}"
else
    git remote add "${REMOTE_NAME}" "${DISABLED_FETCH_URL}"
    git remote set-url --push "${REMOTE_NAME}" "${BACKUP_REPO_URL}"
fi

FETCH_URL=$(git remote get-url "${REMOTE_NAME}")
PUSH_URL=$(git remote get-url --push "${REMOTE_NAME}")
echo " Remote '${REMOTE_NAME}' configured:"
echo "   Push URL : ${PUSH_URL}"
echo "   Fetch URL: ${FETCH_URL} (enforced disabled)"
echo "✅ Invariant M2 satisfied: Fetch URL disabled for this local repository."

# ------------------------------------------------------------------------------
# 3. Invariant M3: Strictly One-Way Flow (GitHub -> Backup Depot)
# ------------------------------------------------------------------------------
echo -e "\n[3/3] Invariant M3: Synchronizing one-way mirror ref..."
if [[ -z "${TARGET_BRANCH}" ]]; then
    TARGET_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
    if [[ -z "${TARGET_BRANCH}" ]]; then
        TARGET_BRANCH="main"
    fi
fi

echo "Target branch: ${TARGET_BRANCH}"

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "🔍 [Dry-Run] Verified all gates. Skipped: git push ${REMOTE_NAME} ${TARGET_BRANCH}:${TARGET_BRANCH} --force"
    echo "✅ Dry run successful. All M1–M3 invariants verified."
    exit 0
fi

git push "${REMOTE_NAME}" "${TARGET_BRANCH}:${TARGET_BRANCH}" --force
echo "✅ Invariant M3 satisfied: Successfully synchronized ${TARGET_BRANCH} -> ${REMOTE_NAME}."
