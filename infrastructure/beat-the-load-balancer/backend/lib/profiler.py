#!/usr/bin/env python
# Copyright 2024 Google LLC.
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

import functools
import logging
import time
from typing import Any, Callable


def execution_timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to measure and log the execution time of a function.

    Args:
        func: The function to be decorated.

    Returns:
        The wrapped function.
    """

    @functools.wraps(func)  # Preserve function metadata
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()  # High precision timer
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        logging.debug(
            f"Function '{func.__name__}' took {elapsed_time:.6f} seconds to execute"
        )
        return result

    return wrapper
