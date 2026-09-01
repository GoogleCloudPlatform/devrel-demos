#!/usr/bin/env python3
"""
Bridge Deck CLI Utility.

Provides command-line tools to post, read, inspect pending queries, and reply as the Active Agent.
Usage:
  ./venv/bin/python github/src/bridge_cli.py post "Your prompt" --sender Antigravity --mode claude_direct
  ./venv/bin/python github/src/bridge_cli.py read --limit 5
  ./venv/bin/python github/src/bridge_cli.py pending
  ./venv/bin/python github/src/bridge_cli.py reply <tx_id> "My response"
"""

import sys
import json
import argparse
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tenant import get_tenant_dir, DEFAULT_TENANT_ID

DEFAULT_BRIDGE_URL = "http://127.0.0.1:8080"


def get_bridge_paths(tenant_id: str = DEFAULT_TENANT_ID):
    t_dir = get_tenant_dir(tenant_id, base_dir=ROOT_DIR)
    return {
        "dir": t_dir,
        "pending": t_dir / "pending_queries.json",
        "history": t_dir / "history" / "bridge_history.json"
    }

def _post_message_direct(prompt: str, sender: str = "Vector (Implementation Lead)", mode: str = "claude_direct", model: str = "claude-opus-5"):
    print("[+] HTTP endpoint unreachable/blocked; executing in Direct In-Process Mode...")
    try:
        import os
        import time
        import subprocess
        root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root / "src"))
        sys.path.insert(0, str(root.parent / "internal" / "bridge"))
        from model_client import GCPModelClient
        from bridge_runner import build_anthropic_messages_and_system, load_history, save_history

        tx_id = f"tx_{int(time.time())}"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        recipient = "Lumen (Claude Opus 5)" if mode in ["claude_direct", "antigravity_impl"] else "Antigravity"
        recipient_role = "Scientific Advisor" if mode in ["claude_direct", "antigravity_impl"] else "Bridge Deck Lead"
        sender_role = "Implementation Lead" if "Vector" in sender else ("Research Manager" if "Lead" in sender else "Bridge Deck Lead")

        if mode == "antigravity_impl":
            antigravity_resp = prompt
            prompt_to_claude = f"Vector (Implementation Lead) has posted the following update for your review:\n\n{prompt}"
        else:
            antigravity_resp = None
            prompt_to_claude = prompt

        client = GCPModelClient(project_id="YOUR_GCP_PROJECT_ID", location="global", model_name=model)
        msgs, sys_p = build_anthropic_messages_and_system(prompt_to_claude, sender=sender, max_turns=6)
        claude_resp = client.generate(prompt=prompt_to_claude, max_output_tokens=8192, messages_list=msgs, system_prompt=sys_p)

        new_tx = {
            "id": tx_id,
            "timestamp": now_iso,
            "mode": mode,
            "sender": sender,
            "sender_role": sender_role,
            "recipient": recipient,
            "recipient_role": recipient_role,
            "subject": f"{sender} Query ({mode})",
            "prompt_text": prompt,
            "antigravity_response": antigravity_resp,
            "claude_response": claude_resp,
            "thinking_blocks": ["Direct in-process execution completed."],
            "raw_request_json": {"source": "bridge_cli_direct"},
            "raw_response_json": {"status": "success"}
        }

        data = load_history()
        data.setdefault("transactions", []).append(new_tx)
        save_history(data)

        print(f"[✓] DIRECT BRIDGE TRANSACTION SUCCESS ({tx_id})")
        print(f"Sender: {sender} | Mode: {mode}")
        print(f"\n--- PROMPT ({sender}) ---")
        print(prompt)
        if antigravity_resp:
            print("\n--- ANTIGRAVITY / VECTOR NOTE ---")
            print(antigravity_resp)
        if claude_resp:
            print("\n--- LUMEN RESPONSE ---")
            print(claude_resp)
        return True
    except Exception as e:
        print(f"[!] Direct execution error: {e}")
        return False

def post_message(prompt: str, sender: str = "Vector (Implementation Lead)", mode: str = "claude_direct", model: str = "claude-opus-5", bridge_url: str = DEFAULT_BRIDGE_URL):
    url = f"{bridge_url}/api/chat"
    payload = {
        "prompt": prompt,
        "sender": sender,
        "mode": mode,
        "model": model,
        "location": "global"
    }

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with opener.open(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                tx = res.get("transaction", {})
                print(f"[✓] BRIDGE TRANSACTION SUCCESS ({tx.get('id', 'N/A')})")
                print(f"Sender: {tx.get('sender')} | Mode: {tx.get('mode')}")
                print(f"\n--- PROMPT ({tx.get('sender')}) ---")
                print(tx.get('prompt_text'))
                if tx.get('antigravity_response'):
                    print("\n--- ANTIGRAVITY / VECTOR NOTE ---")
                    print(tx['antigravity_response'])
                if tx.get('claude_response'):
                    print("\n--- CLAUDE RESPONSE ---")
                    print(tx['claude_response'])
            else:
                print(f"[!] Bridge API error response: {res.get('error')}")
    except Exception as e:
        print(f"[!] HTTP Connection error to {bridge_url} ({e}); falling back to direct mode...")
        _post_message_direct(prompt, sender, mode, model)

def read_history(limit: int = 5, bridge_url: str = DEFAULT_BRIDGE_URL):
    url = f"{bridge_url}/api/history"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            txs = data.get("transactions", [])[-limit:]
            print(f"=== LAST {len(txs)} BRIDGE TRANSACTIONS ===")
            for tx in txs:
                print(f"\nID: {tx['id']} | Timestamp: {tx['timestamp']} | Sender: {tx['sender']}")
                print(f"Prompt: {tx['prompt_text'][:100]}...")
                if tx.get('antigravity_response'):
                    print(f"Antigravity/Vector: {tx['antigravity_response'][:120]}...")
                if tx.get('claude_response'):
                    print(f"Claude: {tx['claude_response'][:120]}...")
    except Exception as e:
        print(f"[!] Error fetching history from {bridge_url}: {e}")

def list_pending(tenant_id: str = DEFAULT_TENANT_ID):
    paths = get_bridge_paths(tenant_id)
    pending_file = paths["pending"]
    if not pending_file.exists():
        print("[Queue] No pending queries.")
        return
    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            pending = data.get("pending", {})
            if not pending:
                print("[Queue] No pending queries.")
                return
            print(f"=== PENDING CHAT AGENT QUERIES ({len(pending)}) ===")
            for qid, q in pending.items():
                print(f"\nID: {qid} | Sender: {q.get('sender', 'User')}")
                print(f"Prompt: {q['prompt']}")
    except Exception as e:
        print(f"[!] Error reading pending queries: {e}")

def reply_pending(tx_id: str, response_text: str, tenant_id: str = DEFAULT_TENANT_ID):
    paths = get_bridge_paths(tenant_id)
    history_file = paths["history"]
    pending_file = paths["pending"]

    # 1. Update bridge_history.json
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                hist_data = json.load(f)
            found = False
            for tx in hist_data.get("transactions", []):
                if tx["id"] == tx_id:
                    tx["antigravity_response"] = response_text
                    found = True
                    break
            if found:
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(hist_data, f, indent=2)
                print(f"[✓] Updated transaction '{tx_id}' in {history_file.name} with Active Agent response!")
            else:
                print(f"[!] Transaction '{tx_id}' not found in {history_file.name}.")
        except Exception as e:
            print(f"[!] Error updating bridge history: {e}")

    # 2. Clean up pending_queries.json
    if pending_file.exists():
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                pending_data = json.load(f)
            if tx_id in pending_data.get("pending", {}):
                del pending_data["pending"][tx_id]
                with open(pending_file, "w", encoding="utf-8") as f:
                    json.dump(pending_data, f, indent=2)
                print(f"[✓] Removed query '{tx_id}' from {pending_file.name}.")
        except Exception as e:
            print(f"[!] Error updating pending queue: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bridge Inspector CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Post command
    post_parser = subparsers.add_parser("post", help="Post a message to the bridge")
    post_parser.add_argument("prompt", type=str, help="Prompt text to submit")
    post_parser.add_argument("--sender", type=str, default="Vector (Implementation Lead)", help="Sender name (default: Vector (Implementation Lead))")
    post_parser.add_argument("--mode", type=str, default="claude_direct", choices=["claude_direct", "antigravity_direct", "antigravity_impl", "3way"], help="Discussion mode")
    post_parser.add_argument("--model", type=str, default="claude-opus-5", help="Target model ID")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read recent bridge history")
    read_parser.add_argument("--limit", type=int, default=5, help="Number of transactions to display")

    # Pending command
    subparsers.add_parser("pending", help="List pending queries in queue")

    # Reply command
    reply_parser = subparsers.add_parser("reply", help="Reply to a pending query as Active Agent")
    reply_parser.add_argument("tx_id", type=str, help="Transaction ID to reply to")
    reply_parser.add_argument("response_text", type=str, help="Response text from Active Agent")

    args = parser.parse_args()

    if args.command == "post":
        post_message(prompt=args.prompt, sender=args.sender, mode=args.mode, model=args.model)
    elif args.command == "read":
        read_history(limit=args.limit)
    elif args.command == "pending":
        list_pending()
    elif args.command == "reply":
        reply_pending(tx_id=args.tx_id, response_text=args.response_text)
    else:
        parser.print_help()
