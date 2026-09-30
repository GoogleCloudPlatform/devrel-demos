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

def handle_request(req):
  method = req.get("method")
  req_id = req.get("id")

  # 1. Handle Handshake / Initialization
  if method == "initialize":
    return {
      "jsonrpc": "2.0",
      "id": req_id,
      "result": {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "local-db-server", "version": "1.0.0"}
      }
    }

  # 2. Handle Initialized Notification
  if method == "notifications/initialized":
    return None

  # 3. List Available Tools
  if method == "tools/list":
    return {
      "jsonrpc": "2.0",
      "id": req_id,
      "result": {
        "tools": [
          {
            "name": "get_inventory_eager",
            "description": "Returns current inventory count of items in the local database (eagerly loaded native tool).",
            "inputSchema": {
              "type": "object",
              "properties": {}
            }
          },
          {
            "name": "get_inventory_lazy",
            "description": "Returns current inventory count of items in the local database (lazily loaded proxy tool).",
            "inputSchema": {
              "type": "object",
              "properties": {}
            }
          }
        ]
      }
    }

  # 4. Handle Tool Execution
  if method == "tools/call":
    params = req.get("params", {})
    tool_name = params.get("name")
    if tool_name in ("get_inventory_eager", "get_inventory_lazy"):
      inventory_data = {
        "items": [
          {"sku": "DINO-001", "name": "Velociraptor", "quantity": 4, "status": "Secure"},
          {"sku": "DINO-002", "name": "T-Rex", "quantity": 1, "status": "Paddock 9"}
        ]
      }
      return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
          "content": [
            {"type": "text", "text": json.dumps(inventory_data, indent=2)}
          ]
        }
      }

  # 5. Handle Resources List
  if method == "resources/list":
    return {
      "jsonrpc": "2.0",
      "id": req_id,
      "result": {
        "resources": []
      }
    }

  # 6. Handle Prompts List
  if method == "prompts/list":
    return {
      "jsonrpc": "2.0",
      "id": req_id,
      "result": {
        "prompts": []
      }
    }

  return {
    "jsonrpc": "2.0",
    "id": req_id,
    "error": {"code": -32601, "message": f"Method {method} not found"}
  }

def main():
  while True:
    line = sys.stdin.readline()
    if not line:
      break
    line = line.strip()
    if not line:
      continue
    try:
      req = json.loads(line)
      res = handle_request(req)
      if res:
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()
    except Exception as e:
      err_res = {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32603, "message": str(e)}
      }
      sys.stdout.write(json.dumps(err_res) + "\n")
      sys.stdout.flush()

if __name__ == "__main__":
  main()
