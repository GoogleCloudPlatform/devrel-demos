#!/usr/bin/env python3
"""
bridge_relay.py - Project Bridge Deck Local-to-Cloud Relay Daemon & CLI (Phase 2).

Maintains an outbound-only connection to Google Cloud Run Bridge Deck service,
polling and leasing pending Antigravity tasks, managing task leases with TTL heartbeats,
and resolving responses with compare-and-swap (CAS) persistence.

Usage:
  # Run the background daemon to listen for Astra tasks
  ./venv/bin/python bridge_relay.py run

  # List pending/leased tasks
  ./venv/bin/python bridge_relay.py list

  # Lease next available task (or specific task)
  ./venv/bin/python bridge_relay.py lease [tx_id]

  # Resolve a task with response
  ./venv/bin/python bridge_relay.py resolve <tx_id> "Response text from Astra..."
  ./venv/bin/python bridge_relay.py resolve <tx_id> --file response.txt

  # Release a leased task back to queue
  ./venv/bin/python bridge_relay.py release <tx_id> [lease_id]

  # Check relay connection status
  ./venv/bin/python bridge_relay.py status
"""

import os
import sys
import time
import json
import uuid
import signal
import shutil
import argparse
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

ROOT_DIR = Path(__file__).resolve().parent
MAILBOX_DIR = ROOT_DIR / ".bridge_relay"
CURRENT_TASK_FILE = MAILBOX_DIR / "current_task.json"
REPLY_FILE = MAILBOX_DIR / "reply.txt"
STATUS_FILE = MAILBOX_DIR / "status.json"


def load_env_config() -> Dict[str, str]:
    """Reads configuration from deploy.env and system environment variables."""
    cfg = {}
    deploy_env = ROOT_DIR / "deploy.env"
    if deploy_env.exists():
        try:
            with open(deploy_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass

    for k, v in os.environ.items():
        if k in [
            "BRIDGE_SERVER_URL", "CLOUD_RUN_URL", "BRIDGE_AUTH_TOKEN",
            "BRIDGE_DEFAULT_TENANT", "RELAY_SA_EMAIL", "GOOGLE_CLOUD_PROJECT"
        ]:
            cfg[k] = v

    return cfg


def resolve_auth_token(explicit_token: Optional[str] = None) -> str:
    """Resolves Bridge Deck authentication token from argument, env, or Secret Manager."""
    if explicit_token:
        return explicit_token

    env_cfg = load_env_config()
    if env_cfg.get("BRIDGE_AUTH_TOKEN"):
        return env_cfg["BRIDGE_AUTH_TOKEN"]

    # Try fetching from Secret Manager via gcloud if available
    project = env_cfg.get("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    try:
        cmd = ["gcloud", "secrets", "versions", "access", "latest", "--secret=BRIDGE_AUTH_TOKEN"]
        if project:
            cmd.extend(["--project", project])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    return ""


def get_id_token_for_url(target_url: str, impersonate_sa: Optional[str] = None) -> Optional[str]:
    """Fetches a Google IAM ID token for direct invocation of authenticated Cloud Run services."""
    if not target_url.startswith("https://") or "run.app" not in target_url:
        return None

    try:
        import google.auth
        import google.auth.transport.requests
        from google.oauth2 import id_token

        req = google.auth.transport.requests.Request()
        if impersonate_sa:
            from google.auth import impersonated_credentials
            source_creds, _ = google.auth.default()
            target_creds = impersonated_credentials.IDTokenCredentials(
                source_credentials=source_creds,
                target_principal=impersonate_sa,
                target_audience=target_url
            )
            target_creds.refresh(req)
            return target_creds.token
        else:
            return id_token.fetch_id_token(req, target_url)
    except Exception as e:
        print(f"[!] Note: Could not acquire IAM ID token for {target_url} ({e}). Proceeding without Bearer header.")
        return None


class BridgeRelayClient:
    """Client for communicating with Project Bridge Deck pending and resolve APIs."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        impersonate_sa: Optional[str] = None,
        timeout: int = 15
    ):
        env_cfg = load_env_config()
        self.server_url = (server_url or env_cfg.get("BRIDGE_SERVER_URL") or env_cfg.get("CLOUD_RUN_URL") or "http://127.0.0.1:8081").rstrip("/")
        self.auth_token = resolve_auth_token(auth_token)
        try:
            from core.tenant import DEFAULT_TENANT_ID
        except ImportError:
            DEFAULT_TENANT_ID = "default"
        self.tenant_id = tenant_id or env_cfg.get("BRIDGE_DEFAULT_TENANT") or DEFAULT_TENANT_ID
        self.impersonate_sa = impersonate_sa or env_cfg.get("RELAY_SA_EMAIL")
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _build_request(self, endpoint: str, method: str = "GET", payload: Optional[dict] = None) -> urllib.request.Request:
        url = f"{self.server_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "BridgeDeck-Relay/2.0 (Astra)"
        }
        if self.auth_token:
            headers["X-Bridge-Auth"] = self.auth_token
        if self.tenant_id:
            headers["X-Bridge-Tenant"] = self.tenant_id

        id_token = get_id_token_for_url(self.server_url, impersonate_sa=self.impersonate_sa)
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        return req

    def list_pending(self, status: Optional[str] = None) -> Dict[str, Any]:
        """Lists pending tasks from the bridge server."""
        query = f"?status={urllib.parse.quote(status)}" if status else ""
        req = self._build_request(f"/api/antigravity/pending{query}", method="GET")
        with self.opener.open(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def lease_task(self, worker_id: str = "relay-local", lease_seconds: int = 120) -> Optional[Dict[str, Any]]:
        """Atomically leases the next available pending task."""
        qs = urllib.parse.urlencode({
            "lease": "true",
            "lease_seconds": str(lease_seconds),
            "worker_id": worker_id
        })
        req = self._build_request(f"/api/antigravity/pending?{qs}", method="GET")
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("task")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {e.code} leasing task: {err_body}") from e

    def renew_lease(self, tx_id: str, lease_id: str, lease_seconds: int = 120) -> Optional[Dict[str, Any]]:
        """Renews an active task lease."""
        payload = {
            "action": "renew",
            "tx_id": tx_id,
            "lease_id": lease_id,
            "lease_seconds": lease_seconds
        }
        req = self._build_request("/api/antigravity/pending", method="POST", payload=payload)
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("task")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {e.code} renewing lease: {err_body}") from e

    def release_lease(self, tx_id: str, lease_id: Optional[str] = None) -> bool:
        """Releases an active task lease back to the waiting queue."""
        payload = {
            "action": "release",
            "tx_id": tx_id,
            "lease_id": lease_id
        }
        req = self._build_request("/api/antigravity/pending", method="POST", payload=payload)
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return bool(data.get("success"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {e.code} releasing lease: {err_body}") from e

    def resolve_task(
        self,
        tx_id: str,
        response_text: str,
        lease_id: Optional[str] = None,
        project_id: Optional[str] = None,
        sender: str = "Astra",
        sender_role: str = "Bridge Deck Lead"
    ) -> Dict[str, Any]:
        """Resolves a pending task with response_text via compare-and-swap (CAS)."""
        payload = {
            "tx_id": tx_id,
            "response": response_text,
            "lease_id": lease_id,
            "project_id": project_id,
            "sender": sender,
            "sender_role": sender_role
        }
        req = self._build_request("/api/antigravity/resolve", method="POST", payload=payload)
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {e.code} resolving task: {err_body}") from e


class RelayDaemon:
    """Background polling daemon that leases tasks, writes to local mailbox, and manages heartbeats."""

    def __init__(
        self,
        client: BridgeRelayClient,
        poll_interval: float = 3.0,
        lease_ttl: int = 120,
        worker_id: Optional[str] = None
    ):
        self.client = client
        self.poll_interval = poll_interval
        self.lease_ttl = lease_ttl
        self.worker_id = worker_id or f"relay_{os.getpid()}_{uuid.uuid4().hex[:4]}"
        self.running = False
        self.active_task: Optional[Dict[str, Any]] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop_event = threading.Event()

    def _ensure_mailbox(self):
        MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
        if REPLY_FILE.exists():
            REPLY_FILE.unlink()

    def _clean_mailbox(self):
        if CURRENT_TASK_FILE.exists():
            CURRENT_TASK_FILE.unlink()
        if REPLY_FILE.exists():
            REPLY_FILE.unlink()

    def _write_status(self, state: str):
        try:
            MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
            status_data = {
                "state": state,
                "worker_id": self.worker_id,
                "server_url": self.client.server_url,
                "tenant_id": self.client.tenant_id,
                "active_task_id": self.active_task.get("id") if self.active_task else None,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            }
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
        except Exception:
            pass

    def _heartbeat_loop(self, task: Dict[str, Any]):
        tx_id = task["id"]
        lease_id = task["lease_id"]
        interval = max(10, self.lease_ttl // 3)

        while not self._heartbeat_stop_event.wait(interval):
            try:
                renewed = self.client.renew_lease(tx_id, lease_id, lease_seconds=self.lease_ttl)
                if renewed:
                    print(f"[*] Lease renewed for {tx_id} (TTL: {self.lease_ttl}s)")
                else:
                    print(f"[!] Lease renewal returned empty for {tx_id}")
            except Exception as e:
                print(f"[!] Warning: lease renewal failed for {tx_id}: {e}")

    def _start_heartbeat(self, task: Dict[str, Any]):
        self._heartbeat_stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(task,),
            daemon=True,
            name=f"RelayHeartbeat-{task['id']}"
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self):
        self._heartbeat_stop_event.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)
        self._heartbeat_thread = None

    def start(self):
        """Starts the main polling loop."""
        self.running = True
        self._ensure_mailbox()
        self._write_status("listening")

        print("======================================================================")
        print("🚀 BRIDGE DECK LOCAL RELAY DAEMON (PHASE 2)")
        print(f" Worker ID:   {self.worker_id}")
        print(f" Server URL:  {self.client.server_url}")
        print(f" Tenant:      {self.client.tenant_id}")
        print(f" Poll Period: {self.poll_interval}s | Lease TTL: {self.lease_ttl}s")
        print(f" Mailbox:     {MAILBOX_DIR.resolve()}")
        print("======================================================================")
        print("[*] Polling for pending tasks. Press Ctrl+C to stop.\n")

        while self.running:
            try:
                task = self.client.lease_task(worker_id=self.worker_id, lease_seconds=self.lease_ttl)
                if task:
                    self._handle_leased_task(task)
                else:
                    time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                print("\n[*] Stopping relay daemon...")
                break
            except Exception as e:
                print(f"[!] Relay poll error: {e}. Retrying in {self.poll_interval}s...")
                time.sleep(self.poll_interval)

        self.stop()

    def _handle_leased_task(self, task: Dict[str, Any]):
        self.active_task = task
        self._write_status("working")

        tx_id = task.get("id", "unknown")
        sender = task.get("sender", "User")
        sender_role = task.get("sender_role", "Operator")
        recipient = task.get("recipient", "Astra")
        project_id = task.get("project_id", "lantern")
        prompt = task.get("prompt", "")

        print("\n" + "=" * 70)
        print(f"🔔 NEW TASK LEASED: [{tx_id}]")
        print(f" Sender:    {sender} ({sender_role})")
        print(f" Recipient: {recipient}")
        print(f" Project:   {project_id}")
        print(f" Prompt:\n{prompt.strip()}")
        print("-" * 70)
        print(f" Mailbox file created: {CURRENT_TASK_FILE.name}")
        print(f" 👉 Write your reply into {REPLY_FILE.name} or use:")
        print(f"    ./venv/bin/python bridge_relay.py resolve {tx_id} \"Your response text\"")
        print("=" * 70 + "\n")

        with open(CURRENT_TASK_FILE, "w", encoding="utf-8") as f:
            json.dump(task, f, indent=2)

        self._start_heartbeat(task)

        # Wait for reply via reply.txt, terminal input, or external resolution
        try:
            resolved = False
            last_external_check = 0.0
            while self.running and not resolved:
                if REPLY_FILE.exists():
                    try:
                        reply_text = REPLY_FILE.read_text(encoding="utf-8").strip()
                        if reply_text:
                            print(f"[*] Found reply in {REPLY_FILE.name} ({len(reply_text)} chars). Resolving...")
                            res = self.client.resolve_task(
                                tx_id=tx_id,
                                response_text=reply_text,
                                lease_id=task.get("lease_id"),
                                project_id=project_id,
                                sender=recipient,
                                sender_role="Bridge Deck Lead"
                            )
                            print(f"[✓] Task {tx_id} resolved successfully! Server status: {res.get('status')}")
                            resolved = True
                            break
                    except Exception as re_err:
                        print(f"[!] Error resolving from reply.txt: {re_err}")

                # Check if task was resolved externally (every 10 seconds to reduce server load)
                now = time.time()
                if now - last_external_check >= 10.0:
                    last_external_check = now
                    try:
                        pending_check = self.client.list_pending(status="all")
                        active_ids = [t.get("id") for t in pending_check.get("tasks", [])]
                        if tx_id not in active_ids:
                            print(f"[*] Task {tx_id} was resolved externally. Resuming polling.")
                            resolved = True
                            break
                    except Exception:
                        pass

                time.sleep(1.0)
        finally:
            self._stop_heartbeat()
            self._clean_mailbox()
            self.active_task = None
            self._write_status("listening")

    def stop(self):
        """Stops the daemon and cleans up active leases if needed."""
        self.running = False
        self._stop_heartbeat()
        if self.active_task:
            tx_id = self.active_task.get("id")
            lease_id = self.active_task.get("lease_id")
            print(f"[*] Releasing lease for task {tx_id} on shutdown...")
            try:
                self.client.release_lease(tx_id, lease_id=lease_id)
            except Exception as e:
                print(f"[!] Failed to release lease: {e}")
        self._clean_mailbox()
        self._write_status("stopped")
        print("[✓] Relay daemon cleanly stopped.")


# ------------------------------------------------------------------------------
# CLI Subcommands
# ------------------------------------------------------------------------------

def cmd_run(args):
    client = BridgeRelayClient(
        server_url=args.url,
        auth_token=args.token,
        tenant_id=args.tenant,
        impersonate_sa=args.impersonate_sa
    )
    daemon = RelayDaemon(
        client=client,
        poll_interval=args.interval,
        lease_ttl=args.lease_ttl,
        worker_id=args.worker_id
    )

    def _sig_handler(sig, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    daemon.start()


def cmd_list(args):
    client = BridgeRelayClient(server_url=args.url, auth_token=args.token, tenant_id=args.tenant)
    res = client.list_pending(status=args.status)
    tasks = res.get("tasks", [])
    count = res.get("count", len(tasks))

    print(f"\n=== PENDING BRIDGE DECK TASKS ({count}) ===")
    if not tasks:
        print("  (No tasks currently in queue)")
        return

    for t in tasks:
        tid = t.get("id")
        sender = t.get("sender", "User")
        recipient = t.get("recipient", "Astra")
        status = t.get("status", "waiting")
        lease_id = t.get("lease_id")
        leased_by = t.get("leased_by")
        exp = t.get("lease_expires_at")
        time_left = f" (expires in {int(exp - time.time())}s)" if exp and exp > time.time() else ""
        prompt_snippet = (t.get("prompt") or "")[:80].replace("\n", " ")

        print(f"\n• ID: {tid} | Status: [{status.upper()}]{time_left}")
        print(f"  From: {sender} ➔ To: {recipient} | Project: {t.get('project_id', 'lantern')}")
        if leased_by:
            print(f"  Worker: {leased_by} (Lease ID: {lease_id})")
        print(f"  Prompt: {prompt_snippet}...")


def cmd_lease(args):
    client = BridgeRelayClient(server_url=args.url, auth_token=args.token, tenant_id=args.tenant)
    task = client.lease_task(worker_id=args.worker_id or "cli-worker", lease_seconds=args.lease_ttl)
    if not task:
        print("[*] No tasks available to lease.")
        return

    print(f"[✓] LEASE ACQUIRED: {task.get('id')}")
    print(f"Lease ID:    {task.get('lease_id')}")
    print(f"Expires at:  {task.get('lease_expires_at')} ({args.lease_ttl}s)")
    print(f"From:        {task.get('sender')}")
    print(f"Prompt:\n{task.get('prompt')}")


def cmd_resolve(args):
    client = BridgeRelayClient(server_url=args.url, auth_token=args.token, tenant_id=args.tenant)
    response_text = ""
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"[!] Error: File '{args.file}' not found.")
            sys.exit(1)
        response_text = p.read_text(encoding="utf-8").strip()
    elif args.response:
        response_text = args.response.strip()
    else:
        print("[!] Error: You must supply response text or specify --file <path>.")
        sys.exit(1)

    res = client.resolve_task(
        tx_id=args.tx_id,
        response_text=response_text,
        lease_id=args.lease_id,
        project_id=args.project_id,
        sender=args.sender,
        sender_role=args.sender_role
    )
    print(f"[✓] Task '{args.tx_id}' resolved successfully!")
    print(f"Project: {res.get('project_id')} | Status: {res.get('status')}")


def cmd_release(args):
    client = BridgeRelayClient(server_url=args.url, auth_token=args.token, tenant_id=args.tenant)
    ok = client.release_lease(tx_id=args.tx_id, lease_id=args.lease_id)
    if ok:
        print(f"[✓] Lease for task '{args.tx_id}' released back to queue.")
    else:
        print(f"[!] Failed to release lease for task '{args.tx_id}'.")


def cmd_status(args):
    client = BridgeRelayClient(server_url=args.url, auth_token=args.token, tenant_id=args.tenant)
    print("=== BRIDGE DECK RELAY STATUS ===")
    print(f" Server URL: {client.server_url}")
    print(f" Tenant:     {client.tenant_id}")
    print(f" Auth Token: {'***' + client.auth_token[-6:] if client.auth_token else '(not set)'}")

    try:
        res = client.list_pending()
        tasks = res.get("tasks", [])
        waiting = sum(1 for t in tasks if t.get("status") == "waiting")
        leased = sum(1 for t in tasks if t.get("status") == "leased")
        print(f" Connectivity: 🟢 CONNECTED (HTTP 200)")
        print(f" Queue Stats:  {len(tasks)} total ({waiting} waiting, {leased} leased)")
    except Exception as e:
        print(f" Connectivity: 🔴 ERROR ({e})")


def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--url", help="Bridge server URL (default: CLOUD_RUN_URL or http://127.0.0.1:8081)")
    parent_parser.add_argument("--token", help="Bridge authentication token")
    parent_parser.add_argument("--tenant", help="Tenant ID (default: BRIDGE_DEFAULT_TENANT or default)")
    parent_parser.add_argument("--impersonate-sa", help="Google Cloud service account email to impersonate")

    parser = argparse.ArgumentParser(
        description="Bridge Deck Local-to-Cloud Relay Utility (Phase 2)",
        parents=[parent_parser]
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # run (daemon)
    p_run = subparsers.add_parser("run", help="Run relay daemon in background polling loop", parents=[parent_parser])
    p_run.add_argument("--interval", type=float, default=3.0, help="Polling interval in seconds (default: 3.0)")
    p_run.add_argument("--lease-ttl", type=int, default=120, help="Task lease duration in seconds (default: 120)")
    p_run.add_argument("--worker-id", help="Worker identifier string")

    # list
    p_list = subparsers.add_parser("list", help="List pending and leased tasks", parents=[parent_parser])
    p_list.add_argument("--status", choices=["waiting", "leased", "all"], default="all", help="Status filter")

    # lease
    p_lease = subparsers.add_parser("lease", help="Lease the next available task", parents=[parent_parser])
    p_lease.add_argument("--lease-ttl", type=int, default=120, help="Task lease duration in seconds (default: 120)")
    p_lease.add_argument("--worker-id", help="Worker identifier string")

    # resolve
    p_resolve = subparsers.add_parser("resolve", help="Resolve a pending task with a response", parents=[parent_parser])
    p_resolve.add_argument("tx_id", help="Transaction ID to resolve")
    p_resolve.add_argument("response", nargs="?", help="Response text string")
    p_resolve.add_argument("--file", help="Path to file containing response text")
    p_resolve.add_argument("--lease-id", help="Active lease ID if held")
    p_resolve.add_argument("--project-id", help="Target project ID")
    p_resolve.add_argument("--sender", default="Astra", help="Sender name (default: Astra)")
    p_resolve.add_argument("--sender-role", default="Bridge Deck Lead", help="Sender role")

    # release
    p_release = subparsers.add_parser("release", help="Release a leased task back to waiting queue", parents=[parent_parser])
    p_release.add_argument("tx_id", help="Transaction ID to release")
    p_release.add_argument("--lease-id", help="Active lease ID")

    # status
    subparsers.add_parser("status", help="Check connectivity and queue status", parents=[parent_parser])

    args = parser.parse_args()

    if not args.command or args.command == "run":
        cmd_run(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "lease":
        cmd_lease(args)
    elif args.command == "resolve":
        cmd_resolve(args)
    elif args.command == "release":
        cmd_release(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
