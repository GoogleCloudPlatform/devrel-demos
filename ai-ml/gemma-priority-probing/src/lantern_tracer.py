#!/usr/bin/env python3

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

"""
Project Lantern: OpenTelemetry & Arize Phoenix Telemetry Tracer.
Instruments agent execution traces, J-Lens activation readouts, and computes IAFR.
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from j_lens_gemma import GEMMA_MODEL_CONFIGS

class LanternTracer:
    """
    Telemetry and IAFR (Information Attributable Failure Rate) tracker for Project Lantern.
    """
    def __init__(self, experiment_name: str = "project_lantern_iafr_baseline", model_id: str = "google/gemma-4-e4b"):
        self.experiment_name = experiment_name
        self.model_id = model_id
        config = GEMMA_MODEL_CONFIGS.get(model_id, list(GEMMA_MODEL_CONFIGS.values())[0])
        self.j_space_window = config["j_space_window_prior"]
        self.traces: List[Dict[str, Any]] = []
        self.phoenix_active = False
        self._init_phoenix()

    def _init_phoenix(self):
        try:
            import phoenix as px
            from pathlib import Path
            root = Path(__file__).resolve().parent.parent.parent
            phoenix_dir = root / "internal" / "phoenix"
            phoenix_dir.mkdir(parents=True, exist_ok=True)
            os.environ["PHOENIX_WORKING_DIR"] = str(phoenix_dir)
            px.launch_app(port=6006)
            self.phoenix_active = True
            print("[+] Arize Phoenix Telemetry Visualizer initialized on http://localhost:6006")
        except Exception as e:
            print(f"[!] Arize Phoenix session warning: {e}. Traces will be logged to local trace JSON.")

    def log_agent_run(
        self,
        prompt_id: str,
        category: str,
        prompt_text: str,
        stale_target: str,
        recent_target: str,
        selected_output: str,
        j_space_top_tokens: Dict[int, List[tuple]]
    ):
        """
        Record a single agent execution trace and classify IAFR failure status.
        """
        # Determine if output matches stale doc (Information Attributable Failure) vs recent doc
        is_iafr_failure = (stale_target.lower() in selected_output.lower()) and not (recent_target.lower() in selected_output.lower())
        is_success = (recent_target.lower() in selected_output.lower())
        
        trace = {
            "timestamp": time.time(),
            "prompt_id": prompt_id,
            "category": category,
            "prompt_text": prompt_text,
            "stale_target": stale_target,
            "recent_target": recent_target,
            "selected_output": selected_output,
            "iafr_failure": is_iafr_failure,
            "success": is_success,
            "j_space_top_tokens_window": {
                layer: j_space_top_tokens.get(layer, [])
                for layer in range(self.j_space_window[0], self.j_space_window[1] + 1)
            }
        }
        self.traces.append(trace)

    def compute_iafr_metrics(self) -> Dict[str, Any]:
        """
        Compute overall and per-category Information Attributable Failure Rate (IAFR).
        """
        total = len(self.traces)
        if total == 0:
            return {"iafr_percentage": 0.0, "total_runs": 0}
            
        iafr_failures = sum(1 for t in self.traces if t["iafr_failure"])
        successes = sum(1 for t in self.traces if t["success"])
        ambiguous = total - iafr_failures - successes
        
        categories = {}
        for t in self.traces:
            cat = t["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "iafr_failures": 0}
            categories[cat]["total"] += 1
            if t["iafr_failure"]:
                categories[cat]["iafr_failures"] += 1

        category_iafr = {
            cat: (data["iafr_failures"] / data["total"]) * 100
            for cat, data in categories.items()
        }
        
        return {
            "total_runs": total,
            "iafr_failures": iafr_failures,
            "iafr_rate_percent": (iafr_failures / total) * 100,
            "success_rate_percent": (successes / total) * 100,
            "ambiguous_rate_percent": (ambiguous / total) * 100,
            "category_iafr_breakdown": category_iafr
        }

    def export_traces(self, filepath: str = "lantern_telemetry_traces.json"):
        metrics = self.compute_iafr_metrics()
        export_data = {
            "experiment_name": self.experiment_name,
            "summary_metrics": metrics,
            "traces": self.traces
        }
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)
        print(f"[+] Exported telemetry traces and IAFR metrics to {Path(filepath).resolve()}")
