# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import json
import datetime
from pathlib import Path

def main():
    stage = "PreToolUse" if "--pre" in sys.argv else ("PostToolUse" if "--post" in sys.argv else "ToolUse")
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        payload = {"error_parsing_input": str(e)}

    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "stage": stage,
        "conversationId": payload.get("conversationId"),
        "stepIdx": payload.get("stepIdx"),
        "toolCall": payload.get("toolCall"),
        "error": payload.get("error")
    }

    workspace_paths = payload.get("workspacePaths")
    if workspace_paths and len(workspace_paths) > 0:
        log_file = Path(workspace_paths[0]) / "plugin_tool_audit.log"
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass

    if stage == "PreToolUse":
        print(json.dumps({"decision": "allow"}))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
