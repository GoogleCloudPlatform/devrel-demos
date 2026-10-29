#!/usr/bin/env python3
"""
Run the 300-case 3-judge live benchmark for `safety-gate` against `test_corpus.json`.

The corpus contains 300 cases across all three stages (`150` Stage 1, `110` Stage 2, `40` Stage 3):
1. Stage 1 deterministic rules (150 cases: 100 allow + 50 deny).
   Real fast-allow commands and file reads, plus hard-deny commands and file/MCP calls.
2. Stage 2 fast AI judge (`gemini-3.1-flash-lite-preview`, 110 cases: 70 allow + 40 deny).
   Real gray-area developer commands (git, gh, kubectl, gcloud, curl) plus adversarial look-alikes.
3. Stage 3 full-context AI judge (`gemini-3.1-pro-preview`, 40 cases: 20 allow + 20 deny).
   The same high-impact command is allowed or denied depending on what the user asked,
   including prompt-injection attempts hidden in untrusted tool output.

Usage: python3 test_corpus.py [--backend gcp] [--workers 8]
"""

import argparse
import concurrent.futures
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

os.environ.setdefault("SAFETY_GATE_HOME_ALIASES", os.pathsep.join(("/Users/alice", "/home/alice")))
os.environ.setdefault("SAFETY_GATE_HEAVY_TIMEOUT_SECONDS", "10.0")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safety_gate as sg

CORPUS_FILE = Path(__file__).resolve().parent / "test_corpus.json"


def run_live_benchmark(
    backend: str = os.environ.get("SAFETY_GATE_BACKEND", "gcp"),
    workers: int = 8,
    corpus_path: Path = CORPUS_FILE,
) -> Dict[str, Any]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    cases = corpus["cases"]

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        orig_state = sg.STATE_DIR
        orig_cache = sg.CACHE_FILE
        orig_lock = sg.CACHE_LOCK_FILE
        orig_rules = sg.RULES_FILE
        orig_brain = sg.BRAIN_ROOTS
        orig_override = sg._CLI_BACKEND_OVERRIDE

        sg.STATE_DIR = td_path
        sg.CACHE_FILE = td_path / "bench-cache.json"
        sg.CACHE_LOCK_FILE = td_path / "bench-cache.lock"
        sg.RULES_FILE = td_path / "bench-rules.json"
        sg._CLI_BACKEND_OVERRIDE = ""

        # Carry over backend discovery and API key files from the real state dir.
        for src_dir in (Path(sg.DEFAULT_STATE_DIR), Path.home() / ".config" / "safety-gate"):
            if not src_dir.is_dir():
                continue
            for real_env in src_dir.glob("*-env.json"):
                shutil.copyfile(real_env, td_path / real_env.name)
            for key_name in ("api_key", "gemini_api_key", ".gemini_api_key"):
                kp = src_dir / key_name
                if kp.is_file() and not (td_path / key_name).exists():
                    shutil.copyfile(kp, td_path / key_name)
        sg.set_configured_backend(backend)

        fake_brain = td_path / "brain"
        fake_brain.mkdir(parents=True, exist_ok=True)
        sg.BRAIN_ROOTS = (fake_brain,) + tuple(orig_brain)

        try:
            case_transcripts: Dict[str, Tuple[str, str]] = {}
            for c in cases:
                cid = f"bench-{c['id']}"
                log_dir = fake_brain / cid / ".system_generated" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                t_file = log_dir / "transcript.jsonl"
                steps = [
                    {
                        "step_index": 1,
                        "type": "USER_INPUT",
                        "content": c.get("user_input") or "<USER_REQUEST>Inspect workspace.</USER_REQUEST>",
                    }
                ]
                if c.get("untrusted_tool_output"):
                    steps.append(
                        {
                            "step_index": 2,
                            "type": "TOOL_RESPONSE",
                            "content": str(c["untrusted_tool_output"]),
                        }
                    )
                t_file.write_text("\n".join(json.dumps(s) for s in steps) + "\n", encoding="utf-8")
                case_transcripts[c["id"]] = (cid, str(t_file))

            def eval_one(c: Dict[str, Any]) -> Dict[str, Any]:
                t0 = time.time()
                cid, t_path = case_transcripts[c["id"]]
                payload = {
                    "conversationId": cid,
                    "transcriptPath": t_path,
                    "toolCall": {
                        "name": c["tool"],
                        "args": c["args"],
                    },
                }
                out, stg, target = sg.evaluate_tool_call(payload)
                dec = out.get("decision")
                rsn = out.get("reason", "")
                elapsed_ms = round((time.time() - t0) * 1000.0, 1)
                return {
                    "id": c["id"],
                    "judge": c.get("judge", ""),
                    "category": c["category"],
                    "expected": c["expected_decision"],
                    "actual": dec,
                    "stage": stg,
                    "reason": rsn,
                    "target": target,
                    "ms": elapsed_ms,
                    "passed": dec == c["expected_decision"],
                }

            t_start = time.time()
            results: List[Dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(eval_one, c) for c in cases]
                for fut in concurrent.futures.as_completed(futs):
                    results.append(fut.result())
            wall_s = round(time.time() - t_start, 2)
        finally:
            sg.STATE_DIR = orig_state
            sg.CACHE_FILE = orig_cache
            sg.CACHE_LOCK_FILE = orig_lock
            sg.RULES_FILE = orig_rules
            sg.BRAIN_ROOTS = orig_brain
            sg._CLI_BACKEND_OVERRIDE = orig_override

    results.sort(key=lambda r: r["id"])
    allow_results = [r for r in results if r["expected"] == "allow"]
    deny_results = [r for r in results if r["expected"] == "deny"]
    allow_passed = sum(1 for r in allow_results if r["passed"])
    deny_passed = sum(1 for r in deny_results if r["passed"])
    failures = [r for r in results if not r["passed"]]

    judge_breakdown: Dict[str, Dict[str, int]] = {}
    for j_key in ("stage1", "stage2", "stage3"):
        j_res = [r for r in results if r.get("judge") == j_key]
        j_allow = [r for r in j_res if r["expected"] == "allow"]
        j_deny = [r for r in j_res if r["expected"] == "deny"]
        judge_breakdown[j_key] = {
            "total": len(j_res),
            "passed": sum(1 for r in j_res if r["passed"]),
            "allow_passed": sum(1 for r in j_allow if r["passed"]),
            "allow_total": len(j_allow),
            "deny_passed": sum(1 for r in j_deny if r["passed"]),
            "deny_total": len(j_deny),
        }

    return {
        "backend": backend,
        "total": len(results),
        "passed": allow_passed + deny_passed,
        "allow_total": len(allow_results),
        "allow_passed": allow_passed,
        "deny_total": len(deny_results),
        "deny_passed": deny_passed,
        "by_judge": judge_breakdown,
        "wall_seconds": wall_s,
        "failures": failures,
    }




def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 300-case 3-judge live safety-gate corpus benchmark")
    parser.add_argument(
        "--backend",
        default=os.environ.get("SAFETY_GATE_BACKEND", "gcp"),
        help="Classifier backend (default: gcp, the public Gemini API)",
    )
    parser.add_argument("--workers", type=int, default=8, help="Concurrent worker threads (default: 8)")
    args = parser.parse_args()

    res = run_live_benchmark(backend=args.backend, workers=args.workers, corpus_path=CORPUS_FILE)
    print(
        json.dumps(
            {
                "backend": res["backend"],
                "total": res["total"],
                "passed": res["passed"],
                "allow": f"{res['allow_passed']}/{res['allow_total']}",
                "deny": f"{res['deny_passed']}/{res['deny_total']}",
                "by_judge": res["by_judge"],
                "wall_seconds": res["wall_seconds"],
                "failure_count": len(res["failures"]),
                "failures": res["failures"][:10],
            },
            indent=2,
        )
    )
    return 0 if len(res["failures"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
