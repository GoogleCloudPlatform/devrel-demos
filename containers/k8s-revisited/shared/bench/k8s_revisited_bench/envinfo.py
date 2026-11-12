# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Capture the run environment as JSON: versions, nodes, kernel, git commit.

Usage: python3 -m k8s_revisited_bench.envinfo --out results/env.json [--context CTX]
"""
import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys


def _run(cmd, timeout=20):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def kubectl(args, context=None):
    if not shutil.which("kubectl"):
        return None
    cmd = ["kubectl"] + (["--context", context] if context else []) + args
    return _run(cmd)


def node_summary(context=None):
    raw = kubectl(["get", "nodes", "-o", "json"], context)
    if not raw:
        return []
    nodes = []
    for item in json.loads(raw).get("items", []):
        labels = item["metadata"].get("labels", {})
        info = item.get("status", {}).get("nodeInfo", {})
        nodes.append({
            "name": item["metadata"]["name"],
            "pool": labels.get("cloud.google.com/gke-nodepool", ""),
            "machineType": labels.get("node.kubernetes.io/instance-type", ""),
            "kubeletVersion": info.get("kubeletVersion"),
            "osImage": info.get("osImage"),
            "kernelVersion": info.get("kernelVersion"),
            "containerRuntimeVersion": info.get("containerRuntimeVersion"),
            "capacity": item.get("status", {}).get("capacity", {}),
        })
    return nodes


def collect(context=None):
    version = kubectl(["version", "-o", "json"], context)
    return {
        "collectedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "context": context or kubectl(["config", "current-context"]),
        "kubectlVersion": json.loads(version) if version else None,
        "nodes": node_summary(context),
        "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
        "gitCommit": _run(["git", "rev-parse", "HEAD"]),
        "env": {k: os.environ[k] for k in ("PINNED_FLASH_MODEL", "PROJECT_ID", "ZONE") if k in os.environ},
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="results/env.json")
    p.add_argument("--context", help="kubectl context (default: current)")
    args = p.parse_args(argv)
    data = collect(args.context)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
