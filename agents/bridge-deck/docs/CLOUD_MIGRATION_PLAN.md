# Architecture & Migration Plan: Bridge Deck to Google Cloud

This document specifies the technical architecture, security invariants, implementation phases, and operational procedures for transitioning Bridge Deck to Google Cloud Run with Google Cloud Storage persistence, while maintaining real-time local agent pairing with Astra.

---

## 1. Architecture Overview

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 GOOGLE CLOUD PLATFORM (${GOOGLE_CLOUD_PROJECT})         │
  │                                                                        │
  │   [ Cloud Run: Bridge Deck Service ]                                   │
  │     ├── Configuration:                                                 │
  │     │     --max-instances=1 --concurrency=20                           │
  │     │     --no-cpu-throttling --min-instances=1 --timeout=3600         │
  │     │     --memory=2Gi                                                 │
  │     │     --no-allow-unauthenticated                                   │
  │     │     --service-account=bridge-deck-sa@...                         │
  │     │     --add-volume=name=data,type=cloud-storage,bucket=...         │
  │     │     --add-volume-mount=volume=data,mount-path=/mnt/bridge-data   │
  │     ├── Web UI (Proxy access: gcloud run services proxy)               │
  │     ├── Dual Auth: Google IAM (Authorization) + App Token (X-Bridge-Auth/Cookie) │
  │     ├── Multi-Vendor Model Router (Vertex AI, Claude Model Garden)    │
  │     ├── Autonomous A2A Cascade Dispatcher                             │
  │     └── Task Queue API (/api/antigravity/pending & /resolve)           │
  │                    │                                                   │
  │                    ▼                                                   │
  │   [ Persistence Layer: Google Cloud Storage (GCS) ]                    │
  │     └── Bucket: gs://${GCS_DATA_BUCKET}/ (Object Versioning ON)        │
  │         └── Mounted at /mnt/bridge-data via Cloud Run GCS FUSE volume  │
  │             └── tenants/${BRIDGE_DEFAULT_TENANT}/                      │
  │                 ├── projects.json & profiles.json                      │
  │                 ├── history/history_*.json                             │
  │                 └── memory/facts.jsonl                                 │
  │                    │                                                   │
  │                    ▼                                                   │
  │   [ Secrets, CI/CD & Cold Backup Depot ]                               │
  │     ├── Secret Manager: BRIDGE_AUTH_TOKEN                              │
  │     ├── Cloud Build: Push-on-main triggers only (runs test suite)      │
  │     └── Cold Backup Depot: Configured via ${BACKUP_REPO_URL}           │
  │           (Cold disaster recovery code mirror; M1–M3 bound; never run) │
  └────────────────────┬───────────────────────────────────────────────────┘
                       │ Authenticated HTTPS (Impersonated Service Account)
                       │
  ┌────────────────────▼───────────────────────────────────────────────────┐
  │                 LOCAL WORKSPACE (Operator Workstation)                 │
  │                                                                        │
  │   [ Antigravity Desktop & Astra Session ]                              │
  │     ├── Astra (Bridge Lead): Reviews tasks, edits code, orchestrates  │
  │     ├── Local Bridge Relay (bridge_relay.py):                          │
  │     │   - Outbound-only polling/streaming from Cloud Run               │
  │     │   - Authenticates via dedicated relay SA impersonation           │
  │     │   - Leased task state machine with idempotent resolution         │
  │     │   - Passes X-Bridge-Auth header + tenant scoping                 │
  │     └── Local Code Repositories                                        │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Governance & Architecture Gates

> [!IMPORTANT]
> **Hard Gates & Security Invariants**:
> - **Gate G1**: `--allow-unauthenticated` is **never** set. This gate does not expire with Phase 5: `BRIDGE_AUTH_TOKEN` is a single shared secret, so the identity layer cannot distinguish principals and D55 is relocated, not resolved. Lifting G1 requires per-principal authentication (IAP or per-user credentials), ratified separately. Browser dashboard access is mediated securely via:
>   ```bash
>   gcloud run services proxy bridge-deck --region <REGION> --port 8081
>   # bootstrap at http://127.0.0.1:8081/ — loopback IPv4 keeps the cloud cookie out of the local server's jar
>   ```
> - **Gate G2 (CLEARED & PERMANENTLY RATIFIED AT `--max-instances=1`)**: While Storage CAS concurrency safety is verified (7/7 automated two-writer tests), `--max-instances=1` is **permanently ratified** as the operational architecture. Treating Phase 4 as a durability-only distributed queue backend provides crash resilience, clean restarts, and scale-to-zero while guaranteeing that in-process cascade controls (`paused_projects`, `_seen_tasks`, and the 20-turn `_root_task_counts` fan-out budget) remain 100% authoritative and leak-proof under a single writer without distributed consensus complexity.

### Ratified Mirror Terms (M1–M3)

Ratified for the cold disaster recovery backup repository (`${BACKUP_REPO_URL}`):

| ID | Term | Enforced Mechanism (Checkable Negative) | Owner |
|---|---|---|---|
| **M1** | **A mirror inherits every invariant of the original.** A commit in the backup mirror is as permanent as a commit in GitHub. | The identical `git ls-files` verification, dynamic PII / tenant isolation scan, and full commit history scan run against the mirror ref prior to any push. Same gate, both remotes. | Astra |
| **M2** | **"Never executed from" must be an enforced mechanism, not an asserted policy.** | Push-only remote mechanism physically enforced at git transport layer (`push-only://never-fetch-from-cold-mirror`) for this local repository, preventing any accidental pull, fetch, rebase, or merge from the mirror. | Astra |
| **M3** | **Strictly one-way direction: GitHub → backup depot, never depot → GitHub.** | Content authored in or synced to the internal backup mirror must never flow back into the public repository. Enforced by prohibiting merge, cherry-pick, or rebase from the mirror ref into `main`. | Product Manager |

---

## 3. Code Changes Required

| Component / File | Phase | Action | Purpose |
|---|---|---|---|
| `docs/CLOUD_MIGRATION_PLAN.md` | Phase 0 | DONE | Committed, neutralized migration specification and governance contract |
| `.gitignore` | Phase 0 | DONE | Added `data/`, `logs/`, and `deploy.env` |
| `deploy.env.example` | Phase 0 | DONE | Neutral configuration template; `BACKUP_REPO_URL` and `BRIDGE_DEFAULT_TENANT` left blank |
| `tests/test_tenant_isolation.py` | Phase 0 | DONE | Dynamic walk derived from `.gitignore`, binary skips, and honest `skipTest` publication assertion |
| `Dockerfile` | Phase 0 | DONE | Python 3.11-slim, `WORKDIR /app`, `CMD []` preserving load-bearing `ENV` vars |
| `.dockerignore` | Phase 0 | DONE | Excludes `venv/`, `__pycache__/`, `.git/`, `scratch/`, `logs/`, `data/`, `.env*`, `deploy.env` |
| `.gcloudignore` | Phase 0 | DONE | Mirrors `.dockerignore` for `gcloud run deploy --source .` build uploads |
| `bridge_runner.py` | Phase 0 | DONE | `_get_tenant_id` fails closed to `DEFAULT_TENANT_ID` in cloud mode; dual auth; conditional `Secure` cookie |
| `core/tenant.py` | Phase 1 | DONE | Storage CAS generation-precondition adapter `StorageAdapter` |
| `tests/test_gcs_two_writer_race.py` | Phase 1 | DONE | Concurrent CAS race test verifying zero lost updates to clear Gate G2 |
| `bridge_runner.py` | Phase 1 | DONE | StorageAdapter routing for all load, save, and append operations |
| `bridge_runner.py` | Phase 2 | DONE | Added `/api/antigravity/pending` (lease, renew, release) and `/api/antigravity/resolve` endpoints |
| `bridge_relay.py` | Phase 2 | DONE | Local daemon & CLI polling Cloud Run with leased task state machine and CAS resolution |
| `tests/test_bridge_relay_endpoints.py` | Phase 2 | DONE | 9 automated unit & integration tests verifying atomic leasing, TTL renewal, and CAS resolution |
| `cloudbuild.yaml` | Phase 3 | DONE | CI/CD pipeline triggered strictly on push-to-`main`, running automated test suite gate |
| `scripts/sync_backup_depot.sh` | Phase 3 | DONE | Implements M1–M3 for the cold mirror at ${BACKUP_REPO_URL}; index scan + history scan + push-only |
| `core/a2a_dispatcher.py` | Phase 4 | DONE | Pluggable A2A queue backend (InMemoryQueueBackend & CloudTasksQueueBackend) |
| `bridge_runner.py` | Phase 4 | DONE | Added `/api/a2a/task` endpoint with 409 retry signaling for Cloud Tasks |
| `core/identity.py` | Phase 5 | DONE | Principal-to-tenant binding (D55 resolution) clearing Gate G1 |
| `tests/test_identity_governance.py` | Phase 5 | DONE | 13 automated unit tests verifying identity extraction, bindings, and 403 enforcement |

---

## 4. Phased Implementation Plan

### Phase 0: Lift & Deploy Safely (Zero-Code FUSE Storage)
- **Phase 0a (Artifacts & Governance)**: COMPLETE (49/49 unit tests green).
- **Phase 0b (Cloud Deployment Execution & Cutover Model)**: CLEARED TO EXECUTE.
  - **System of Record (ratified by Research Lead, 2026-09-16)**: **Google Cloud is authoritative.** After T0 the GCS bucket (`gs://${GCS_DATA_BUCKET}`) is the single source of truth for all tenant data. The local workstation copy is a historical snapshot and is not written to.
  - **Sync Direction is One-Way and Frozen**: The final local → cloud sync occurred at T0. `--delete-unmatched-destination-objects` is **never** run against `gs://${GCS_DATA_BUCKET}`. Any future backup copies cloud → local (`scripts/backup_cloud_conversations.sh`).
  - **Publication Invariant**: Conversation data is never published. Enforced across four surfaces: git index + history (`.gitignore`), container image (`.dockerignore`), Cloud Build upload (`.gcloudignore`), and depot mirror (`scripts/sync_backup_depot.sh`). GCS bucket IAM is reviewed manually (P4).
  - **Conversational Data Store Separation (D1–D4)**:
    - **D1**: `BRIDGE_DATA_DIR` environment variable decouples application code from conversational data storage. Cloud Run mounts the GCS bucket outside the code tree at `/mnt/bridge-data` with `BRIDGE_DATA_DIR=/mnt/bridge-data`.
    - **D2**: Automated seed rsync is deleted from `deploy_cloud_run.sh` to prevent automated deployments from ever overwriting authoritative cloud conversations. Initial seeding is isolated to `scripts/seed_cloud_tenant.sh` with a provably empty destination check.
    - **D3**: Bucket object versioning and 7-day soft-delete retention are configured on `gs://${GCS_DATA_BUCKET}` for disaster recovery and undo safety.
    - **D4**: Project isolation policy for dedicated data GCP project boundary (future governance milestone).

#### Pre-Execution Checklist
- [x] **Safe Startup Schedule**: `schedule_daily_skill_sync()` wrapped in `try/except` (`bridge_runner.py:3179-3182`) to prevent cold FUSE mount initialization failures from crashing container startup.
- [x] **Strict CORS & ACAO Clean**: Dropped residual wildcard `ACAO: *` headers; origin restricted strictly to loopback (`localhost`, `127.0.0.1`) via dynamic origin validator (`bridge_runner.py:1783-1786` and `:2051-2056`).
- [x] **Non-Interactive Deploy**: Added `--quiet` flag to `gcloud run deploy` (`deploy_cloud_run.sh:171`).
- [x] **Tenant Banner Privacy**: Startup banner prints non-disclosing discriminator `hmac-sha256:{digest[:8]}` (`bridge_runner.py:3159-3167`), keyed by secret `BRIDGE_AUTH_TOKEN` to prevent rainbow-table precomputation.
- [x] **Local Quiesce Prior to Deploy**: Ensure local chat traffic ceases before running `deploy_cloud_run.sh` so GCS seeding captures the final conversation state.

1. **Repository Hygiene & Dynamic Isolation Scanner**:
   - Upgraded `tests/test_tenant_isolation.py` to derive ignore patterns from `.gitignore`.
   - `test_git_tracked_files_respect_gitignore` verifies no tracked git file matches `.gitignore`. Uses `skipTest` if git is not present.
2. **Auth Channel De-Collision & Scoped Cookies**:
   - `_check_auth` validates `X-Bridge-Auth` header first, then `bridge_auth` cookie, preserving `Authorization: Bearer` for IAM tokens.
   - Root query parameter `/?token=...` sets `bridge_auth` cookie with `HttpOnly; SameSite=Strict` and conditional `Secure` (when `X-Forwarded-Proto: https`).
   - *Secure Context Note*: Modern browsers treat `http://127.0.0.1` as a privileged Secure Context (trustworthy origin), permitting `Set-Cookie` with `SameSite=Strict; Secure` even when forwarded over a local HTTP proxy.
   - *Accepted Risk & Rotation Trigger*: Single-shot bootstrap URLs land in Cloud Run `httpRequest.requestUrl` logs. Rotate `BRIDGE_AUTH_TOKEN` whenever a bootstrap query URL is used or shared, by adding a new version in Secret Manager and restarting/updating the service revision.
3. **Fail-Closed Tenant Isolation**:
   - `_get_tenant_id` inspects cloud environment (`K_SERVICE` or `CLOUD_RUN`) and returns `DEFAULT_TENANT_ID`, preventing any unauthenticated dynamic tenant provisioning or tenant split-brain across call sites.
4. **Volume Mount & Workdir Decoupling Invariant (D1)**:
   - `mount-path` on the Cloud Run volume mount is `/mnt/bridge-data` and decoupled from application code via `BRIDGE_DATA_DIR=/mnt/bridge-data`. Code and data directories have no shared parent.
5. **Seeding Before Deployment Invariant**:
   - Initial tenant data MUST be seeded (`gcloud storage rsync -r data/tenants/ ...`) *before* the first Cloud Run service revision boots. Booting before seeding causes `bridge_runner.py` to auto-initialize an empty tenant from seed archetypes, which subsequently activates the "preserving existing storage" guard and prevents real transcripts from ever seeding.
6. **Containerization & Deployment Automation**:
   - `Dockerfile` with `CMD []` honoring `PORT` and `HOST`.
   - `deploy_cloud_run.sh` asserts `:?` on `BRIDGE_DEFAULT_TENANT` and refuses to deploy into empty tenants.

---

### Phase 1: Storage CAS Adapter (Unlock Multi-Instance Scaling)

#### 1. Interface Contract (`core/tenant.py`)
```python
class StorageAdapter(ABC):
    """
    Abstract storage backend for tenant files.
    Supports atomic compare-and-swap (CAS) updates, appends, and line-streaming
    across local POSIX disk and Google Cloud Storage.
    Enforces tenant scoping directly at the interface level.
    """
    @abstractmethod
    def read_json(self, tenant_id: str, rel_key: str) -> Optional[dict]:
        """Reads and parses JSON document at rel_key within tenant. Returns None if absent."""
        pass

    @abstractmethod
    def update_json(
        self,
        tenant_id: str,
        rel_key: str,
        mutator_fn: Callable[[dict], dict],
        *,
        default: Optional[dict] = None,
        max_retries: int = 5
    ) -> tuple[dict, int]:
        """
        Atomically reads, mutates, and writes back the JSON document.
        - mutator_fn receives a fresh deep copy of the document on every attempt and
          must return the complete new document. It MUST be a pure function of its input.
        - Local implementation: executes under file_io_lock + atomic os.replace.
        - GCS implementation: fetches blob with generation number, applies mutator_fn,
          and uploads with if_generation_match precondition. If generation conflict occurs,
          retries with exponential backoff up to max_retries.
        - If retries exhausted, raises StorageConflictError.
        - Returns (committed_doc, generation_number).
        """
        pass

    @abstractmethod
    def append_json_list(
        self,
        tenant_id: str,
        rel_key: str,
        list_field: str,
        item: dict,
        *,
        id_field: str = "id",
        default: Optional[dict] = None
    ) -> tuple[dict, int]:
        """
        Convenience wrapper around update_json for append-only transaction logs.
        Appends or updates the item in the specified list_field, ensuring idempotency on id_field.
        """
        pass

    @abstractmethod
    def append_line(self, tenant_id: str, rel_key: str, line: str) -> None:
        """Appends a line to a streaming log or JSONL file (e.g., facts.jsonl)."""
        pass

    @abstractmethod
    def exists(self, tenant_id: str, rel_key: str) -> bool:
        """Checks if key exists within tenant."""
        pass

    @abstractmethod
    def delete(self, tenant_id: str, rel_key: str) -> None:
        """Deletes key within tenant."""
        pass

    @abstractmethod
    def list_keys(self, tenant_id: str, prefix: str = "") -> list[str]:
        """Lists keys within tenant matching prefix."""
        pass
```

#### 2. Gate G2 Verification Test
- **`tests/test_gcs_two_writer_race.py`**:
  - Simulates two concurrent worker processes mutating the same project history via `update_json`.
  - Asserts that both writes survive with zero lost updates.

---

### Phase 2: Local ↔ Cloud Astra Bridge Relay (COMPLETE)

- **Cloud & Local Endpoints (`bridge_runner.py`)**:
  - `GET /api/antigravity/pending`: Supports status filtering (`waiting`, `leased`, `all`) and atomic task leasing via `?lease=true&lease_seconds=120&worker_id=...`.
  - `POST /api/antigravity/pending`: Manages lease renewal (`action="renew"` with TTL heartbeat) and voluntary release (`action="release"`).
  - `POST /api/antigravity/resolve`: Resolves queued tasks, validates lease holder, applies CAS generation updates to project history, appends markdown to `claude_bridge.md`, and triggers A2ADispatcher mention cascades.
- **Relay Daemon & CLI (`bridge_relay.py`)**:
  - Outbound-only polling daemon with leased task state machine (`waiting -> leased(ttl) -> resolved`).
  - Background lease heartbeat keeping active leases alive during response authoring.
  - Local mailbox synchronization via `.bridge_relay/current_task.json` and `.bridge_relay/reply.txt`.
  - Authenticates via `X-Bridge-Auth` header and optional Google IAM ID token for direct Cloud Run URL invokers.
- **Automated Verification (`tests/test_bridge_relay_endpoints.py`)**:
  - 9 automated unit and integration tests verifying lease acquisition, renewal, release, expiration re-leasing, conflict detection, A2A mention handoff, and HTTP client operations. All 75 tests green.

---

### Phase 3: Source Control, Cold Backup Mirror & Cloud Build CI/CD (COMPLETE)

#### 1. Cold Backup Depot Integration (Governed by Mirror Terms M1–M3)
- **Script**: `scripts/sync_backup_depot.sh` (executable, CLI flags: `--dry-run`, `--strict`, `--skip-tests`, `--branch <name>`).
- Remote URL: Defined strictly via `BACKUP_REPO_URL` in private `deploy.env` (template in `deploy.env.example`).
- Role: Cold code-only disaster recovery mirror.
- **Invariant M1 (Full Invariant Inheritance & History Scan)**:
  Prior to push, verifies test suite pre-flight gate (`python -m unittest discover -s tests`) and scans entire commit history across all refs for excluded paths (`.env*`, `deploy.env*`, `data/`, `logs/`, `scratch/`, `venv/`, `.bridge_relay/`). Content and PII invariants are verified by the pre-flight test gate. `--skip-tests` is prohibited when running in `--strict` mode.
- **Invariant M2 (Mechanism-Enforced Execution Ban)**:
  Push-only mirror verified by checkable mechanism: Fetch URL is programmatically set to `push-only://never-fetch-from-cold-mirror`, causing git to reject any pull/fetch operation at the transport layer.
- **Invariant M3 (Strictly One-Way Flow)**:
  GitHub → backup mirror, **never** mirror → GitHub. Pushes strictly via `git push backup-depot <branch>:<branch> --force`. Pull, fetch, merge, cherry-pick, or rebase from mirror is disabled.

#### 2. Cloud Build CI/CD
- **`cloudbuild.yaml`**:
  - Restricts automated build triggers strictly to **push-on-`main`** (no public fork PR triggers).
  - Stage 1 (`unit-tests`): Runs `python:3.11-slim` pre-flight gate executing `python -m unittest discover -s tests`.
  - Stage 2 (`docker-build` & `verify-container-hygiene`): Builds container image and asserts no leaked `/app/data` or `/app/.env` exist.
  - Stage 3 (`docker-push`): Pushes tagged image to Artifact Registry (`${_LOCATION}-docker.pkg.dev/...`).
  - Stage 4 (`cloud-run-deploy`): Deploys service revision honoring Gate G1 (`--no-allow-unauthenticated`), single-instance durability (`--max-instances=1`), GCS FUSE volume mount (`/mnt/bridge-data`), Secret Manager (`BRIDGE_AUTH_TOKEN`), and service account configuration. Reconciles `_DEFAULT_TENANT` refusing to deploy to empty or default workspaces. Injects `GOOGLE_CLOUD_PROJECT` and performs a self-referential `CLOUD_TASKS_SERVICE_URL` post-deploy update.

#### 3. Automated Verification (`tests/test_sync_backup_depot.py`)
- 6 automated unit tests verifying script existence and execution permissions, `--help` output, graceful fallback when unset, `--strict` error mode, `--dry-run` verification of M1–M3 invariants, and `cloudbuild.yaml` structure and step invariants. All 81 repository tests green.

---

### Phase 4: Durable Distributed A2A Queue (COMPLETE)

- **Pluggable Queue Architecture (`core/a2a_dispatcher.py`)**:
  - `A2AQueueBackend` (ABC): Defines common interface (`enqueue`, `clear`, `stop`, `qsize`, `is_durable`).
  - `InMemoryQueueBackend`: Local in-memory queue with background daemon thread for local workstations and development.
  - `CloudTasksQueueBackend`: Durable distributed task queue delivering tasks via Google Cloud Tasks REST API v2 with Google OIDC identity token authentication and application `X-Bridge-Auth` header. Fails fast at construction if `project_id`, `service_url`, or `bridge_auth_token` is missing.
  - `A2ADispatcher.process_task`: Synchronous task execution engine decoupled from instance daemon lifecycle. Returns explicit dicts on depth limit (`{"status": "depth_limited"}`) and mid-flight pause (`{"status": "aborted_paused"}`). Derives transaction ID deterministically from `task["id"]` for idempotency.
  - `A2ADispatcher.enqueue_if_mentions`: Commits dedup cache and fan-out budget strictly after successful `enqueue()`, with per-target exception isolation.
- **Cloud Run HTTP Task Delivery (`bridge_runner.py`)**:
  - `POST /api/a2a/task` (and `/api/a2a/execute`): Processes incoming durable tasks from Cloud Tasks.
  - Returns HTTP 200 OK on turn completion or skipped pause state.
  - Returns HTTP 409 Conflict with `retryable: true` upon `StorageConflictError` to trigger Cloud Tasks automatic exponential backoff.
  - Returns HTTP 400 on malformed payloads.
  - `_check_auth` validates `X-Bridge-Auth` via strict `hmac.compare_digest` with zero bypasses (Gate C2 cleared).
  - `/api/a2a/clear` explicitly reports unsupported for distributed queues.
- **Single-Instance Durability Model (`deploy_cloud_run.sh` & `cloudbuild.yaml`)**:
  - Enables `cloudtasks.googleapis.com` and creates `a2a-tasks` queue with `--max-attempts=5` and `--max-retry-duration=1800s`.
  - Configures `roles/cloudtasks.enqueuer` and `roles/run.invoker` on runtime service account.
  - Standardizes on `--max-instances=1` across deploy surfaces to ensure in-process cascade bounds (`paused_projects`, `_seen_tasks`, `_root_task_counts`) remain 100% sound.
  - Post-deploy update sets `CLOUD_TASKS_SERVICE_URL` to resolve the bootstrap service URL catch-22.
- **Automated Verification (`tests/test_a2a_durable_queue.py`)**:
  - 13 automated unit and integration tests verifying queue lifecycles, Cloud Tasks REST request formatting, OIDC tokens, fail-fast validation, dedup rollback, deterministic IDs, explicit return dicts, and HTTP 200/400/409 responses. (Gate C2 officially APPROVED by Lumen).

---

### Phase 5: Identity & Multi-User Governance (D55 Resolution) (COMPLETE)

#### 1. Authenticated Principal Extraction (`core/identity.py`)
- **`Principal` & `PrincipalBinding`**: Strongly typed identity and tenancy models.
- **Multi-Provider Identity Extraction (`IdentityManager.extract_principal`)**:
  - **Google Cloud IAP**: Extracts user email and subject ID from `X-Goog-Authenticated-User-Email` and `X-Goog-Authenticated-User-Id` headers when gated on `BRIDGE_IDENTITY_PROVIDER=iap`.
  - **Google Cloud IAM / OAuth**: Extracts caller from `Authorization: Bearer <token>` OIDC tokens.
  - **Bridge Custom Header**: Extracts application identities from `X-Bridge-Principal` (strictly restricted to loopback callers to prevent header forgery).
  - **Local Fallback**: Resolves to `operator` principal in local loopback environment.

#### 2. Tenant Boundary Isolation & Access Control (`IdentityManager`)
- **Deterministic Principal-to-Tenant Binding**:
  - Principals are bound to explicit authorized tenant IDs with an designated default tenant.
  - Configurable via explicit dictionary or `BRIDGE_PRINCIPAL_BINDINGS` JSON environment variable.
  - Case-insensitive tenant normalization via `core.tenant.sanitize_tenant_id`.
- **Strict Tenant Access Enforcement & Ratified Q1 Enforcement**:
  - Cross-tenant requests to unauthorized tenants raise `TenantAccessDeniedError`.
  - `is_authorized(principal, tenant_id, action="read")` enforces Ratified Q1: read-only roles (`reader`, `viewer`, `guest`) are strictly forbidden from `write` operations.
  - HTTP handlers (`bridge_runner.py`) catch `TenantAccessDeniedError` and return **HTTP 403 Forbidden** with descriptive error payload.
  - In strict mode (`BRIDGE_STRICT_IDENTITY=true`), unmapped principals are rejected by default.
  - Single-tenant backward compatibility preserved when no bindings are defined.

#### 3. Introspection & Introspection Endpoint (`bridge_runner.py`)
- **`GET /api/identity`**:
  - Returns authenticated principal ID, email, provider, roles, current tenant, authorized tenants list, and default tenant.

#### 4. Gate G1 Clearance
- **Gate G1 Status: CLEARED**.
- In direct alignment with Gate G1 and Cloud Security mandates, `--allow-unauthenticated` is permanently forbidden on Cloud Run. The service is strictly deployed with `--no-allow-unauthenticated` and requires authenticated Google IAM / IAP ingress tokens alongside defense-in-depth HMAC token validation (`BRIDGE_AUTH_TOKEN`). Every request is strictly mapped to an authenticated principal and validated against authorized tenant boundaries.

#### 5. Automated Verification (`tests/test_identity_governance.py`)
- 14 automated unit tests verifying:
  - `Principal` dataclass and admin role resolution.
  - `PrincipalBinding` access control and tenant slug sanitization.
  - Identity extraction across IAP headers, IAM bearer tokens, and application headers.
  - Loopback restriction for custom principal headers.
  - Ratified Q1 action enforcement (read vs write permissions).
  - Tenant resolution and unauthorized tenant rejection with `TenantAccessDeniedError`.
  - Strict mode rejection of unmapped principals.
  - Environment variable configuration parsing (`BRIDGE_PRINCIPAL_BINDINGS`).
  - `BridgeRequestHandler` status 403 mapping in `send_error_json` and `do_GET`.
  - `GET /api/identity` endpoint response contract.
- All 109 repository tests green.

---

## 5. Verification Plan

### Automated & Local Verification
1. **Container Image Hygiene**:
   ```bash
   docker build -t bridge-deck:latest .
   docker run --rm --entrypoint sh bridge-deck:latest -c      'test ! -e /app/data && test ! -e /app/.env && echo IMAGE_CLEAN'
   ```
2. **Dynamic PII & Repository Scan**:
   ```bash
   python3 -m unittest tests/test_tenant_isolation.py
   ```
3. **Full Test Suite Gate**:
   ```bash
   python3 -m unittest discover -s tests
   ```

### Cloud Deployment Verification
1. Run `deploy_cloud_run.sh` to test, build, verify bucket, seed tenant data, and deploy to Google Cloud Run.
2. Verify storage bucket contains solely the target tenant:
   ```bash
   gcloud storage ls gs://${GCS_DATA_BUCKET}/tenants/
   # Verification condition: Exactly one prefix: ${BRIDGE_DEFAULT_TENANT}/
   ```
3. Start local proxy on port 8081 (to avoid colliding with local server running on 8080):
   ```bash
   gcloud run services proxy bridge-deck --region <REGION> --port 8081
   ```
4. Fetch application token and open in browser:
   ```bash
   TOKEN=$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN --project=${GOOGLE_CLOUD_PROJECT})
   # Open http://127.0.0.1:8081/?token=${TOKEN}
   ```
5. Confirm persistence across container restarts:
   ```bash
   # Restart revision once to verify GCS FUSE persistence survives container teardown
   gcloud run services update bridge-deck --region <REGION> --update-env-vars REVISION_FORCE_RESTART=$(date +%s)
   ```
