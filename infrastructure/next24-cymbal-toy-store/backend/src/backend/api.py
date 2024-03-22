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
