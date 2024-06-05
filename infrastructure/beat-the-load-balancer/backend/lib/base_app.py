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
"""
A base flask app to inherit.
"""
import logging
import os
import time

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from lib import config
from lib.system_config import SystemIPConfig
from lib.system_health import SystemLoad
from lib.celery_task import celery_app

app = Flask("load-balancing-blitz")
app.config["SECRET_KEY"] = "the quick brown fox jumps over the lazy dog"
app.config["CORS_HEADERS"] = "Content-Type"

# cors = CORS(app, resources={r"/foo": {"origins": "http://localhost:port"}})
cors = CORS(app)

# to tell Flask it is Behind a Proxy - https://flask.palletsprojects.com/en/2.3.x/deploying/proxy_fix/
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# app config to treat "/index" and "/index/" as same.
app.url_map.strict_slashes = False
# Settings
HOSTNAME = os.uname().nodename
FILE = __file__
APP_URLS = """
/load
/health
/update/system_address
/clear_celery_jobs
/version
""".strip().splitlines()


def create_index_page(hostname, filename, urls):
    # clean up filename
    if os.path.sep in filename:
        filename = filename.split(os.path.sep)[-1]
    if filename.endswith(".py"):
        filename = filename.split(".")[0].upper() + " App"

    # html page
    html_content = [
        f"<p>Script:  <b>{filename}</b></p>",
        f"<p>Hostname:  <b>{hostname}</b></p><hr>",
    ]

    # html nav bar
    urls = list(set(urls))
    urls.sort()

    # nav_bar = ['<div class="topnav"> <h4>All Urls/Nav Bar</h4>']
    nav_bar = ["<div> <h4>All Urls/Nav Bar</h4>"]
    for i, url in enumerate(urls):
        nav_bar.append(f'-----<a href="{url}">{i + 1}. url: {url}___</a>-----')
    nav_bar.append("</div>")
    html_content += nav_bar

    return render_template(
        "default.html",
        hostname=hostname,
        filename=filename,
        urls=urls,
        html_block="",
    )


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/load")
def load():
    return SystemLoad().get_system_health(live_data=True)


@app.route("/update/system_address")
def report_system_address():
    try:
        logging.debug("Running get_live_ip_config_info()")
        logging.debug(SystemIPConfig().update_ip_address())
        return {"status": "ok"}
    except Exception:
        logging.exception("Failed to fetch information")
        return {"status": "not ok"}


@app.route("/hc")
@app.route("/health")
def health_check():
    return {"status": "ok"}


@app.route("/version")
def get_version():
    return {
        "hostname": config.HOSTNAME,
        "version": config.GAME_VERSION,
        "uptime": time.time() - config.GAME_APP_START_TIME,
    }


@app.route("/purge_celery_queue")
def purge_local_celery_queues():
    logging.warning("Clearing Celery job queues")
    cleared_jobs = celery_app.control.purge()
    logging.warning(f"Cleared {cleared_jobs} jobs")
    return {"status": "ok"}
