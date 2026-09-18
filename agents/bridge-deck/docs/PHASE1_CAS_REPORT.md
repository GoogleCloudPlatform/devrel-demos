# Executive Report: Phase 1 CAS Storage Adapter & Gate G2 Concurrency Safety

**Author**: Astra (Bridge Deck Lead)  
**Date**: September 16, 2026  
**Project**: Project Bridge Deck (`${BRIDGE_PROJECT_ID}`)  
**Status**: Amendments A1–A7 Implemented & Verified (60/60 Tests Passing) | Gate G2 Verification Packet Submitted for Scientific Advisor (Lumen) Review

---

## 1. Executive Summary

Phase 1 of the Bridge Deck Cloud Migration addresses the multi-process and multi-instance concurrency defect inherent in Cloud Storage FUSE (last-write-wins without POSIX cross-process file locks). 

By implementing an explicit Compare-And-Swap (CAS) `StorageAdapter` layer utilizing Google Cloud Storage generation match tokens (`if_generation_match`), Bridge Deck will eliminate data loss and clobbered history under concurrent writer workloads once Gate G2 is formally cleared.

Scientific Advisor Status: **Gate G2 remains NOT signed off.** Lumen approved the remediation plan with A1–A3 as blocking amendments and A4–A7 as non-blocking hardening items. All amendments (A1–A7) have now been implemented, verified via the red-first A3 production race test, confirmed by 60/60 passing tests, and deployed to Cloud Run revision `bridge-deck-00010-c7h` under `--max-instances=1`. This packet is submitted for Lumen's official Gate G2 review.

---

## 2. Phase 1 Implementation & Verification

### StorageAdapter Architecture
- **`StorageAdapter` (ABC)**: Formal abstract contract in `core/tenant.py` for read, CAS mutation, and atomic updates. Blind `write_json` has been eliminated; whole-document writes require `replace_json(..., max_retries=1)`.
- **`LocalStorageAdapter`**: Employs `fcntl.flock` cross-process locking and atomic temporary file replacement (`.tmp` + `os.replace`), maintaining full backward compatibility for local macOS/Linux development.
- **`GCSStorageAdapter`**: Uses `google.cloud.storage.Client` directly over HTTPS/gRPC with `if_generation_match=blob.generation` preconditions and exponential backoff with jitter.

### Write-Site Census
Every tenant write site across the codebase was refactored away from direct POSIX file I/O to route 100% through `StorageAdapter`:
- `bridge_runner.py`: `save_profiles`, `save_projects`, `save_history`, `append_transaction`, `save_skill_usage`, `save_engines`, `save_models`, `save_persona`, `update_agent`, `delete-project`, `delete-persona`, and `pending_queries.json`.
- `memory/store.py`: `append_semantic_fact`, `save_shared_decision`, `get_shared_decisions`.

### Concurrency & Multi-Process Verification
1. **Red-First Two-Process Race Test (`tests/test_two_process_race.py`)**:
   - **RED Baseline** (Naive uncoordinated POSIX read-modify-write): `Expected: 40, Actual: 20, Lost: 20` (50% data loss under concurrent processes).
   - **GREEN Verification** (`LocalStorageAdapter` with flock + atomic replace): `Expected: 50, Actual: 50, Lost: 0` (zero lost updates across 5 concurrent OS processes; `_lock_degraded` verified `False`).
2. **GCS CAS Concurrency Suite (`tests/test_gcs_two_writer_race.py`)**:
   - 8/8 tests passing in 0.3s verifying GCS 412 `PreconditionFailed` handling, backoff, retry exhaustion (`StorageConflictError`), update idempotency, and the A3 production race test (`save_history` vs. `append_transaction`).
3. **Repository Suite**: 60 / 60 tests passing cleanly across unit, tenant isolation, and concurrency suites.

---

## 3. Production Cloud Run Runtime Verification

Direct inspection of Cloud Run revision `bridge-deck-00010-c7h` confirmed:
```text
$ gcloud run services describe bridge-deck --region us-central1 --format='value(spec.template.spec.containers[0].env)'
{'name': 'BRIDGE_DEFAULT_TENANT', 'value': '${BRIDGE_DEFAULT_TENANT}'};
{'name': 'CLOUD_RUN', 'value': 'true'};
{'name': 'GCS_DATA_BUCKET', 'value': '${GCS_DATA_BUCKET}'};
{'name': 'BRIDGE_AUTH_TOKEN', 'valueFrom': {'secretKeyRef': {'key': 'latest', 'name': 'BRIDGE_AUTH_TOKEN'}}}
```
- Runtime logs confirm: `Storage Adapter: GCSStorageAdapter`.
- Cloud tool reach: Container paths dynamically resolve `/app` allowing Lumen's inspection tools (`read_file`, `list_dir`, `grep_search`) full codebase visibility.
- `--max-instances=1` remains actively deployed and enforced, strictly honoring Hard Gate G2.

---

## 4. Scientific Advisor (Lumen) Review & Completed Amendments

| ID | Amendment | Classification | Status | Description |
|---|---|---|---|---|
| **A1** | Eliminate Silent Overwrite Loops | 🔴 Blocker | ✅ Completed | Eliminated blind `write_json`. Introduced `replace_json(..., max_retries=1)` so whole-document overwrites fail loud immediately on generation mismatch. |
| **A2** | Define Caller-Side Conflict Handling | 🔴 Blocker | ✅ Completed | Caught `StorageConflictError` in HTTP request dispatch (`send_error_json` / `do_POST`), responding with HTTP 409 (`{"success": false, "error": "concurrent modification, retry"}`). In A2A dispatcher, caught and logged structured warning so worker threads survive. |
| **A3** | Production Race Test Case | 🔴 Blocker | ✅ Completed | Added `test_production_race_save_history_vs_append_transaction` in `tests/test_gcs_two_writer_race.py` racing `save_history` vs. `append_transaction`. Verified RED on unconditioned overwrite, then GREEN asserting `StorageConflictError` on stale write and survival of the appended transaction. |
| **A4** | JSON Corruption Refusal | 🟠 Hardening | ✅ Completed | In `update_json` (where inline parsing occurs without calling `read_json`), raised `StorageCorruptError` on invalid JSON rather than substituting `{}`. |
| **A5** | Split Environment Predicates | 🟡 Hardening | ✅ Completed | Separated environment posture (`is_cloud() -> bool`) from storage destination (`use_gcs_storage() -> bool`), preserving `CLOUD_RUN_DIRECT_GCS` for local-to-cloud testing. |
| **A6** | Unhook Memory Store from FUSE | 🟡 Hardening | ✅ Completed | Added `read_lines` to `StorageAdapter` for `get_semantic_facts`. Updated `ensure_dirs()` in `memory/store.py` to no-op when `use_gcs_storage()` is active or adapter is non-local. |
| **A7** | Startup Diagnostic Banner | 🟡 Hardening | ✅ Completed | Added `Storage Adapter: <ClassName>` to startup banner in `run_server`, logging `Storage Adapter: GCSStorageAdapter` in Cloud Run. |

---

## 5. Next Steps to Gate G2 Sign-Off & Multi-Instance Scaling

1. **Scientific Advisor Review**: Present updated code, test results, and restored Cloud reach to Lumen in Project Bridge Deck (`${BRIDGE_PROJECT_ID}`).
2. **Official Gate G2 Sign-Off**: Receive Lumen's explicit sign-off on Gate G2 data criteria.
3. **Raise `--max-instances`**: Once Gate G2 is formally cleared by Lumen and the Product Lead, proceed to multi-instance Cloud Run scaling.
