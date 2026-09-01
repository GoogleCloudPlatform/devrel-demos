#!/usr/bin/env python3
"""
Bridge Deck Antigravity Task Listener / Queue Watcher.
Monitors pending_queries.json for queued workspace tasks and notifies the Antigravity agent session.
"""

import sys
import time
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tenant import get_tenant_dir, DEFAULT_TENANT_ID


def get_pending_file(tenant_id: str = DEFAULT_TENANT_ID) -> Path:
    return get_tenant_dir(tenant_id, base_dir=ROOT_DIR) / "pending_queries.json"


def monitor_queue(poll_interval: float = 2.0, tenant_id: str = DEFAULT_TENANT_ID):
    pending_file = get_pending_file(tenant_id)
    print(f"[+] Bridge Deck Antigravity Task Watcher active for tenant '{tenant_id}' (polling every {poll_interval}s)...")
    seen_ids = set()
    
    # Initialize seen_ids with resolved tasks and suppress stale waiting tasks (> 2h old)
    stale_count = 0
    now = time.time()
    if pending_file.exists():
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.get("pending", {}).items():
                    if v.get("status") != "waiting":
                        seen_ids.add(k)
                    else:
                        is_stale = False
                        if k.startswith("tx_") and k[3:].isdigit():
                            tx_epoch = int(k[3:])
                            if now - tx_epoch > 7200:
                                is_stale = True
                        if is_stale:
                            seen_ids.add(k)
                            stale_count += 1
        except Exception:
            pass

    if stale_count > 0:
        print(f"[i] Startup: Suppressed {stale_count} stale waiting tasks (>2h old).")

    while True:
        try:
            if pending_file.exists():
                with open(pending_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pending_dict = data.get("pending", {})
                    
                    for tx_id, item in pending_dict.items():
                        if tx_id not in seen_ids and item.get("status") == "waiting":
                            seen_ids.add(tx_id)
                            sender = item.get("sender", "Team Member")
                            recipient = item.get("recipient", "Antigravity")
                            prompt = item.get("prompt", "")
                            
                            print("=" * 60)
                            print(f"🔔 [NEW ANTIGRAVITY TASK DETECTED: {tx_id}]")
                            print(f"From: {sender} -> To: {recipient}")
                            print(f"Prompt: {prompt[:300]}...")
                            print("=" * 60)
                            sys.stdout.flush()
        except json.JSONDecodeError:
            # Atomic save in progress, retry on next cycle
            pass
        except Exception as e:
            print(f"[!] Watcher error: {e}", file=sys.stderr)

        time.sleep(poll_interval)


if __name__ == "__main__":
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    monitor_queue(poll_interval=interval)
