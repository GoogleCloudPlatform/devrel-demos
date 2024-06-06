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

import chat_handler
import connector
import contextlib
import logging
import uvicorn
import typing
import sys
import os

from starlette.applications import Starlette
from starlette.config import Config
from starlette.responses import JSONResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from backend.api import routes

from dotenv import load_dotenv

load_dotenv()
config = Config(".env")

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 404:
            response = await super().get_response('.', scope)
        return response

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'])
]


class State(typing.TypedDict):
    chat_be: chat_handler.ChatHandler


def lifespan(app: Starlette) -> typing.AsyncIterator[State]:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s','%m-%d %H:%M:%S')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    SECRET_ID = config("DB_USER_SECRET_ID")
    PROJECT_ID = config("GCP_PROJECT")

    if "DB_PASS" in os.environ:
        db_password = os.environ["DB_PASS"]
    else:
        db_password = connector.get_secret(SECRET_ID, PROJECT_ID)

    DB_NAME = config("DB_NAME")
    DB_USER = config("DB_USER")
    USE_ALLOYDB = config("USE_ALLOYDB")
    if USE_ALLOYDB == "True":
        logging.info("Using Alloydb")
        INSTANCE_HOST = config("INSTANCE_HOST")
        DB_PORT = config("DB_PORT")
        db_connection = connector.connect_with_tcp(INSTANCE_HOST, DB_NAME, DB_USER, db_password, DB_PORT)
    else: 
        INSTANCE_CONNECTION_NAME = config("INSTANCE_CONNECTION_NAME")  # e.g. 'project:region:instance'
        db_connection = connector.connect_with_connector(INSTANCE_CONNECTION_NAME, DB_NAME, DB_USER, db_password)        

    yield {"chat_be" : chat_handler.ChatHandler(db_connection)}


app = Starlette(
    debug=True,
    middleware=middleware,
    lifespan=lifespan,
    routes=[
        Mount('/api', routes=routes),
        Mount('/', SPAStaticFiles(directory='../frontend/out', html=True))
    ]
)

if __name__ == "__main__":
    uvicorn.run("app:app", host='0.0.0.0', port=8080, log_level="info", reload=True)
