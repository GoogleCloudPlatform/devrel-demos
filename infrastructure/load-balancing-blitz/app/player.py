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
import random
import time

import requests
from flask import render_template, redirect

from lib import config
from lib.app_cache import PlayerCache
from lib.base_app import app, APP_URLS, create_index_page
from lib.base_cache import RedisSelectionManager
from lib.helper import JobFileManager
from metrics.metrics import send_game_record_message

# Settings for Index Page
random.seed(42)

APP_URLS += """
/game/start
/game/stop
/vm/all/reset
/vm/all/stats
/vm/active
""".strip().splitlines()

OLD_LOG = """
/process
/rr/process
/load/start
/vm/all
/reset
/process/options
/game
/vm/all
/vm/all/score
/vm/all/load
/vm/all/stats
/vm/active
/vm/score
/vm/active/cache
/vm/active/cache/show
/vm/active/cache/reset
/process
/process/options
/process/auto
/rr/process
"""

# Warehouse VM to redirect the requests
WH_VM_MGR = RedisSelectionManager(config.WH_VM_NAMES)
_DEFAULT_INSTANCE = config.WH_VM_NAMES[0]
WH_VM_MGR.set_selected_vm(_DEFAULT_INSTANCE)

PLAYER_APP_CACHE = PlayerCache()

LOADER_FLAG_FILE = "/tmp/flaskapp_loader_flag_file"
RESET_FLAG_FILE = "/tmp/flaskapp_game_reset_flag_file"

# Additional Settings for Index Page
for _VM in config.WH_VM_NAMES:
    APP_URLS.append(f"/vm/select/{_VM}")


@app.route("/")
def new_index_page():
    return create_index_page(config.HOSTNAME, __file__, APP_URLS)


@app.route("/game")
def game():
    return render_template("game.html", vm_wh_ips=config.VM_IPS)


@app.route("/vm/all", methods=["GET"])
def get_vms_details():
    """For all registered VM details"""
    return PLAYER_APP_CACHE.get_vm_all_ips()


@app.route("/vm/all/score", methods=["GET"])
def get_vms_scores():
    """For all VM provide score details"""
    return PLAYER_APP_CACHE.get_vm_all_scores()


@app.route("/vm/all/load", methods=["GET"])
def get_vms_health():
    """For all VM provide system health details"""
    return PLAYER_APP_CACHE.get_all_vm_health_stats()


@app.route("/vm/all/stats", methods=["GET"])
def get_vms_stats():
    """For selected VM provide all stats(score, health & other)"""
    return PLAYER_APP_CACHE.get_all_vm_stats()


@app.route("/vm/active", methods=["GET"])
def show_active_vm():
    return {
        "active-vm": WH_VM_MGR.get_selected_vm(),
        "active-vm-update-count": WH_VM_MGR.get_vm_selections_count(),
    }


@app.route("/reset", methods=["GET"])
def reset_player_game() -> dict:
    response = dict({"hostname": config.HOSTNAME})
    job_mgr = JobFileManager(RESET_FLAG_FILE, expiry_time=time.time())
    if job_mgr.is_job_running():
        response["status"] = "not ok"
        response["details"] = (
            f"Flag file {RESET_FLAG_FILE} says a job seem to be running"
        )
    else:
        response["status"] = "ok"
        response2 = PLAYER_APP_CACHE.reset()
        response.update(response2)
    return response


@app.route("/vm/select/<vm_name>", methods=["GET"])
def update_vm_select(vm_name) -> dict:
    global WH_VM_MGR
    if vm_name in config.WH_VM_NAMES:
        if vm_name != WH_VM_MGR.get_selected_vm():
            logging.warning(
                f" ===> vm-selection is updated! ({WH_VM_MGR.get_selected_vm()}"
                f" --> {vm_name})"
            )
            WH_VM_MGR.set_selected_vm(vm_name)
            WH_VM_MGR.incr_vm_selection_count()
            # return f"Done! Selected VM:{vm_name}!"
            return {"active-vm": vm_name, "status": "updated"}
        else:
            return {"active-vm": vm_name, "status": "no changes!"}
    else:
        return {
            "active-vm": vm_name,
            "status": "no changes due to invalid input",
            "valid-inputs": config.WH_VM_NAMES,
        }


@app.route("/process")
def automatic_routing():
    ip_address = config.VM_IPS[WH_VM_MGR.get_selected_vm()]
    url = f"http://{ip_address}:8000/process"
    return redirect(url, code=302)


@app.route("/process/options")
def automatic_routing_options() -> dict:
    url_config = {
        vm_name: f"http://{config.VM_IPS[vm_name]}:8000/process"
        for vm_name in config.WH_VM_NAMES
    }
    logging.debug(f"==> /process options {url_config}")
    return url_config


# @app.route("/process/auto")
@app.route("/rr/process")
def automatic_round_robin_routing():
    selected_vm = random.choice(config.WH_VM_NAMES)
    selected_vm_address = config.VM_IPS[selected_vm]
    url = f"http://{selected_vm_address}:8000/process"
    logging.info(
        f"/rr/process - selected vm : {selected_vm} ==> redirect request to {url}"
    )
    return redirect(url, code=302)


@app.route("/vm/reset/<string:vm_name>")
def reset_vm_stats(vm_name=None) -> dict:
    ip_address = config.VM_IPS[vm_name]
    url = f"http://{ip_address}:8000/reset"
    response = send_internal_http_request_to(url)
    return response


@app.route("/vm/all/reset")
@app.route("/game/reset")
def reset_all_vms_stats() -> dict:
    response = dict()
    logging.warning("player: requested reset for Player App Cache")
    response[config.HOSTNAME] = PLAYER_APP_CACHE.reset()

    # reset worker VMS
    for vm_name in config.WH_VM_NAMES + config.LB_WH_VM_NAME:
        logging.warning(f"player: requested reset for Worker({vm_name}) App Cache")
        ip_address = config.VM_IPS[vm_name]

        # purge celery queue
        reset_url = f"http://{ip_address}:8000/purge_celery_queue"
        response[vm_name + "-celery-reset"] = send_internal_http_request_to(reset_url)

        # reset flaskapp cache
        url = f"http://{ip_address}:8000/reset"
        response[vm_name] = send_internal_http_request_to(url)
    logging.warning(f"reset results! {response}")
    return {"status": "ok"}


def send_internal_http_request_to(url) -> dict:
    logging.warning(f"Sending outbound request to {url}")
    response = dict()
    response["url"] = url
    response["request"] = "GET"
    logging.debug(f"==> sending load request to {url}")
    try:
        response["response"] = requests.get(url).json()
        response["status"] = "ok"
    except Exception as err:
        response["status"] = "not ok"
        response["error"] = str(err)
        logging.warning("send_request_to_loader: Found error")
        logging.warning(err)
    return response


def send_request_to_loader(player_name) -> dict:
    logging.warning("Sending request to loader!!!")
    job_mgr = JobFileManager(LOADER_FLAG_FILE, expiry_time=time.time())

    response = dict({"player_name": player_name, "status": "not ok"})

    if job_mgr.is_job_running():
        logging.debug("Locust is recently Triggered. Try again later.")
        response["status"] = "not ok"
        response["details"] = f"A job seem to be running. Found - {LOADER_FLAG_FILE}"
    else:
        try:
            job_mgr.create_timestamp_file()
            #
            ip_address = config.VM_IPS["vm-loader"]
            url = f"http://{ip_address}:8000/load/start"
            response["loader1"] = send_internal_http_request_to(url)
            #
            ip_address = config.VM_IPS["vm-loader2"]
            url = f"http://{ip_address}:8000/load/start"
            response["loader2"] = send_internal_http_request_to(url)
        except Exception as err:
            logging.warning("send_request_to_loader: Found error")
            logging.warning(err)
    return response


def get_player_name(player_name) -> str:
    if player_name == "player":
        # Get the current UTC/GMT time
        current_time = time.gmtime()
        # Format the time as "DD_HH_MM"
        formatted_time = time.strftime("%m%d_%H%M%S", current_time)
        player_name = f"{player_name}_{formatted_time}"
        logging.warning(f"Using player name as `{player_name}`")
    return player_name


@app.route("/game/start")
@app.route("/game/start/<string:player_name>")
def game_start(player_name="player") -> dict:
    # generate unique player id
    player_name = get_player_name(player_name)
    # reset the game stats
    response1 = reset_all_vms_stats()
    # start the game
    PLAYER_APP_CACHE.start_the_game(player_name)
    # start the loader
    response2 = send_request_to_loader(player_name)
    # send the start message to Pubsub
    send_game_record_message("start", uniqueid=player_name)
    return {**response1, **response2}


def send_local_http_call(url):
    try:
        return requests.get(url)
    except Exception:
        logging.exception("failed to API call request")
        return "job failed"


@app.route("/game/stop")
def stop_the_player_game() -> dict:
    send_game_record_message("stop", uniqueid=PLAYER_APP_CACHE.get_player_name())
    try:
        PLAYER_APP_CACHE.stop_the_game()
    except Exception:
        logging.warning("Failed to reset Celery jobs")
    return {
        "status": "ok",
        "message": "Game Timer is reset. Call `/vm/all/reset` before the next game!",
    }


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        filemode="w",
        level=logging.DEBUG,
    )
    app.run(debug=True, port=config.VM_APP_PORTS["vm-main"])
