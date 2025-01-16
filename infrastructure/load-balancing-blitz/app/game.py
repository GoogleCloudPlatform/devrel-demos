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

import logging

from lib import config


logging.basicConfig(
    filename=f"/tmp/flaskapp_game.log",
    format="%(asctime)s - %(message)s",
    filemode="w",
    level=logging.DEBUG,
)


flaskapp = None
if config.HOSTNAME.startswith("vm-loader"):
    from loader import app as loader_app

    flaskapp = loader_app
elif config.HOSTNAME.startswith("vm-main"):
    from player import app as player_app

    # PlayerCache().reset()
    flaskapp = player_app

elif config.HOSTNAME.startswith("vm-wh"):
    from warehouse import app as wh_app

    # WarehouseCache().reset()
    flaskapp = wh_app
    logging.debug("Loading warehouse app")

elif "sampathm" in config.HOSTNAME:
    from player import app as player_app

    flaskapp = player_app

if __name__ == "__main__":
    flaskapp.run(debug=True, port=8000, host="0.0.0.0")
