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
    """Initializes Python root logger making sure Debug and Info
    messages go to STDOUT, while WARNING and above go to STDERR

    Args:
        min_level (int, optional): Minimum logging level.
            Defaults to logging.INFO.
    """
    h_info_and_below = logging.StreamHandler(sys.stdout)
    h_info_and_below.setLevel(logging.DEBUG)
    h_info_and_below.addFilter(lambda record: record.levelno <= logging.INFO)
    h_warn_and_above = logging.StreamHandler(sys.stderr)
    h_warn_and_above.setLevel(logging.WARNING)

    handlers = [h_info_and_below, h_warn_and_above]
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=min_level,
        handlers=handlers,
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
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    mcp.run(transport="http", host=host, port=port)
