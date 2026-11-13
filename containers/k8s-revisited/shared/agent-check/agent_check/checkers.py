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

"""Deterministic checks for model output."""
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import yaml

from .stale_apis import find_stale


@dataclass
class CheckResult:
    name: str
    status: str  # pass | fail | skipped
    detail: str = ""


@dataclass
class CheckContext:
    kube_context: str = ""
    require_all: bool = False
    kubernetes_version: str = "1.37.0"


FENCE = re.compile(r"```(?:ya?ml)?\s*\n(.*?)```", re.S)


def extract_yaml(text):
    """Pull YAML out of a model reply: fenced blocks if present, else the whole reply."""
    blocks = FENCE.findall(text or "")
    return "\n---\n".join(b.strip() for b in blocks) if blocks else (text or "").strip()


def parse_docs(text):
    return [d for d in yaml.safe_load_all(text) if d is not None]


# ------------------------------------------------------------------ path helper
_SEG = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def get_path(obj, path):
    """get_path(doc, "spec.template.spec.initContainers[0].restartPolicy")."""
    cur = obj
    for name, index in _SEG.findall(path):
        if name:
            if not isinstance(cur, dict) or name not in cur:
                return None
            cur = cur[name]
        else:
            i = int(index)
            if not isinstance(cur, list) or i >= len(cur):
                return None
            cur = cur[i]
    return cur


def _docs_of_kind(docs, kind):
    return [d for d in docs if isinstance(d, dict) and d.get("kind") == kind]


def _pod_specs(doc):
    kind = doc.get("kind")
    if kind == "Pod":
        return [doc.get("spec", {})]
    if kind in ("Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job"):
        return [get_path(doc, "spec.template.spec") or {}]
    if kind == "CronJob":
        return [get_path(doc, "spec.jobTemplate.spec.template.spec") or {}]
    return []


def _cpu_value(q):
    if q is None:
        return None
    s = str(q)
    if s.endswith("m"):
        return int(s[:-1]) / 1000.0
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------- individual checks
def check_stale(docs):
    hits = find_stale(docs)
    if hits:
        return CheckResult("stale_apis", "fail", "; ".join(f"{sev}: {msg}" for sev, msg in hits)), len(hits)
    return CheckResult("stale_apis", "pass"), 0


KUBECONFORM_CACHE = os.path.join(tempfile.gettempdir(), "agent-check-kubeconform-cache")


def check_kubeconform(text, ctx, opts):
    """Schema check with kubeconform. Schemas come from AGENT_CHECK_KUBECONFORM_SCHEMAS
    (a local directory or URL template) or, if unset, kubeconform's default schema
    location, cached in a temp directory between runs."""
    binary = shutil.which("kubeconform")
    if not binary:
        return CheckResult("kubeconform", "skipped", "kubeconform not installed")
    version = (opts or {}).get("kubernetes_version", ctx.kubernetes_version)
    cmd = [binary, "-strict", "-summary", "-kubernetes-version", version]
    # A removed apiVersion has no schema, so a missing schema fails by default. Tasks that
    # use CRDs (which have no upstream schema) set ignore_missing_schemas: true.
    if (opts or {}).get("ignore_missing_schemas"):
        cmd.append("-ignore-missing-schemas")
    schemas = os.environ.get("AGENT_CHECK_KUBECONFORM_SCHEMAS")
    if schemas:
        cmd += ["-schema-location", schemas]
    else:
        os.makedirs(KUBECONFORM_CACHE, exist_ok=True)
        cmd += ["-schema-location", "default", "-cache", KUBECONFORM_CACHE]
    cmd.append("-")
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=60)
    status = "pass" if proc.returncode == 0 else "fail"
    return CheckResult("kubeconform", status, (proc.stdout + proc.stderr).strip()[-800:])


def check_server_dry_run(text, ctx):
    if not shutil.which("kubectl"):
        return CheckResult("server_dry_run", "skipped", "kubectl not installed")
    if not ctx.kube_context:
        return CheckResult("server_dry_run", "skipped", "no --context given")
    cmd = ["kubectl", "--context", ctx.kube_context, "apply", "--dry-run=server", "-f", "-"]
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=60)
    status = "pass" if proc.returncode == 0 else "fail"
    return CheckResult("server_dry_run", status, (proc.stdout + proc.stderr).strip()[-800:])


def check_assertions(docs, spec):
    problems = []
    for kind in spec.get("kinds", []):
        if not _docs_of_kind(docs, kind):
            problems.append(f"missing a {kind}")
    for kind, api in (spec.get("api_versions") or {}).items():
        for d in _docs_of_kind(docs, kind):
            if d.get("apiVersion") != api:
                problems.append(f"{kind} should use {api}, found {d.get('apiVersion')}")
    for item in spec.get("field_equals", []):
        matches = _docs_of_kind(docs, item["kind"])
        if not matches or not any(get_path(d, item["path"]) == item["value"] for d in matches):
            problems.append(f"{item['kind']}.{item['path']} should be {item['value']!r}")
    for item in spec.get("field_exists", []):
        matches = _docs_of_kind(docs, item["kind"])
        if not matches or not any(get_path(d, item["path"]) is not None for d in matches):
            problems.append(f"{item['kind']}.{item['path']} should be set")
    qos = spec.get("qos_class")
    if qos == "Guaranteed":
        for d in docs:
            for ps in _pod_specs(d) if isinstance(d, dict) else []:
                for c in ps.get("containers", []):
                    res = c.get("resources", {})
                    lim, req = res.get("limits", {}), res.get("requests", {}) or res.get("limits", {})
                    for r in ("cpu", "memory"):
                        if r not in lim or str(req.get(r)) != str(lim.get(r)):
                            problems.append(f"container {c.get('name')}: {r} requests must equal limits for Guaranteed")
                    if spec.get("integer_cpu"):
                        v = _cpu_value(lim.get("cpu"))
                        if v is None or v != int(v):
                            problems.append(f"container {c.get('name')}: CPU limit must be a whole number")
    elif qos == "Burstable":
        for d in docs:
            for ps in _pod_specs(d) if isinstance(d, dict) else []:
                for c in ps.get("containers", []):
                    res = c.get("resources", {})
                    if not res.get("requests") or res.get("requests") == res.get("limits"):
                        problems.append(f"container {c.get('name')}: needs requests lower than limits for Burstable")
    if problems:
        return CheckResult("assert", "fail", "; ".join(problems))
    return CheckResult("assert", "pass")


def run_checks(text, task, ctx):
    """Run a task's checks against one model reply. Returns (results, stale_hits)."""
    results = []
    stale_hits = 0
    try:
        docs = parse_docs(text)
    except yaml.YAMLError as e:
        return [CheckResult("parse", "fail", str(e)[:300])], 0
    if not docs:
        return [CheckResult("parse", "fail", "no YAML documents in the reply")], 0
    results.append(CheckResult("parse", "pass"))
    for check in task.checks:
        (name, opts), = check.items() if isinstance(check, dict) else ((check, {}),)
        if name == "stale_apis":
            r, stale_hits = check_stale(docs)
        elif name == "kubeconform":
            r = check_kubeconform(text, ctx, opts)
        elif name == "server_dry_run":
            r = check_server_dry_run(text, ctx)
        elif name == "assert":
            r = check_assertions(docs, opts or {})
        else:
            r = CheckResult(name, "skipped", "unknown check")
        results.append(r)
    return results, stale_hits


def verdict(results, require_all=False):
    if any(r.status == "fail" for r in results):
        return False
    if require_all and any(r.status == "skipped" for r in results):
        return False
    return True


def feedback_text(results):
    lines = [f"- {r.name}: {r.detail}" for r in results if r.status == "fail"]
    return "The previous YAML failed these checks:\n" + "\n".join(lines) + "\nReturn the corrected YAML only."
