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

"""Monotonic timers and a CSV recorder for experiment samples."""
import csv
import os
import time
from contextlib import contextmanager


def now_ms():
    """Milliseconds from a monotonic clock (only differences are meaningful)."""
    return time.monotonic_ns() / 1e6


@contextmanager
def timer():
    """with timer() as t: ...; t["ms"] holds the elapsed milliseconds."""
    box = {"ms": None}
    start = now_ms()
    try:
        yield box
    finally:
        box["ms"] = now_ms() - start


class Recorder:
    """Append rows to a CSV file, writing the header once."""

    def __init__(self, path, fields):
        self.path = path
        self.fields = list(fields)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self._f = open(path, "a", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._f, fieldnames=self.fields)
        if new:
            self._w.writeheader()

    def add(self, **row):
        self._w.writerow({k: row.get(k, "") for k in self.fields})
        self._f.flush()

    def close(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
