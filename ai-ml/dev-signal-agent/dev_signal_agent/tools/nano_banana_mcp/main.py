#!/usr/bin/env python
# Copyright 2025 Google LLC
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

import logging
import os
import sys

from fastmcp import FastMCP
from dotenv import load_dotenv

from nano_banana_pro import generate_image


def _initialize_console_logging(min_level: int = logging.INFO):
    """Initializes Python root logger making sure all messages go to STDERR.
    STDOUT is reserved for MCP communication.

    Args:
        min_level (int, optional): Minimum logging level.
            Defaults to logging.INFO.
    """
    handler = logging.StreamHandler(sys.stderr)
    
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=min_level,
        handlers=[handler],
        force=True
    )


tools = [generate_image]
mcp = FastMCP(
    name="MediaGenerators",
    tools=tools
)

if __name__ == "__main__":
    load_dotenv()
    _initialize_console_logging()
    
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        port = int(os.getenv("PORT", 8080))
        host = os.getenv("HOST", "0.0.0.0")
        mcp.run(transport="http", host=host, port=port)
