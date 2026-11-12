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

"""Watch a Kubernetes resource and log each event with a monotonic receive time.

Object timestamps have 1-second resolution, so sub-second measurements use the
time an event reaches the client instead.

Usage: python3 -m k8s_revisited_bench.k8swatch pods -n default --out results/watch.csv [--context CTX]
"""
import argparse
import json
import shutil
import subprocess
import sys

from .timing import Recorder, now_ms

FIELDS = ["recv_ms", "event", "kind", "namespace", "name", "phase", "resourceVersion"]


def watch(resource, namespace=None, context=None, selector=None):
    if not shutil.which("kubectl"):
        raise SystemExit("kubectl not found")
    cmd = ["kubectl"]
    if context:
        cmd += ["--context", context]
    cmd += ["get", resource, "--watch", "--output-watch-events", "-o", "json"]
    cmd += ["-n", namespace] if namespace else ["-A"]
    if selector:
        cmd += ["-l", selector]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    decoder = json.JSONDecoder()
    buf = ""
    for chunk in iter(lambda: proc.stdout.readline(), ""):
        buf += chunk
        while buf.strip():
            try:
                obj, idx = decoder.raw_decode(buf.lstrip())
            except json.JSONDecodeError:
                break
            buf = buf.lstrip()[idx:]
            yield now_ms(), obj


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("resource")
    p.add_argument("-n", "--namespace")
    p.add_argument("-l", "--selector")
    p.add_argument("--context")
    p.add_argument("--out", default="results/watch.csv")
    args = p.parse_args(argv)
    with Recorder(args.out, FIELDS) as rec:
        for recv, ev in watch(args.resource, args.namespace, args.context, args.selector):
            obj = ev.get("object", {})
            meta = obj.get("metadata", {})
            rec.add(recv_ms=f"{recv:.3f}", event=ev.get("type"), kind=obj.get("kind"),
                    namespace=meta.get("namespace"), name=meta.get("name"),
                    phase=obj.get("status", {}).get("phase", ""), resourceVersion=meta.get("resourceVersion"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
