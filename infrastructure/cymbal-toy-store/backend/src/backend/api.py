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

from starlette.responses import JSONResponse
from starlette.endpoints import HTTPEndpoint
from starlette.routing import Route

class Chat(HTTPEndpoint):
    async def post(self, request):
        body = await request.json()
        response = request.state.chat_be.respond(body)
        res_json = {}
        res_json['content'] = {'type':'text','text':f'{response}'}
        return JSONResponse(res_json)


routes = [
  Route("/chat", Chat),
]
