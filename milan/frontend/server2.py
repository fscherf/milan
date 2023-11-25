import argparse
import asyncio
import os

from aiohttp.web import (
    WebSocketResponse,
    HTTPNotFound,
    FileResponse,
    Application,
    Response,
    run_app,
)

from aiohttp import ClientSession, WSMsgType, CookieJar
from yarl import URL

FRONTEND_STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')


class FrontendServer:
    def __init__(self):

        # setup app
        self.app = Application()

        self.app.router.add_route(
            '*',
            '/_milan/frontend{path:.*}',
            self.handle_frontend_request,
        )

        self.app.router.add_route(
            'post',
            '/_milan',
            self.handle_config_request,
        )

        self.app.router.add_route(
            'post',
            '/_milan/',
            self.handle_config_request,
        )

        self.app.router.add_route(
            '*',
            '/{path:.*}',
            self.handle_request,
        )

        self.app.on_shutdown.append(self._stop)

        # internal state
        self.proxy_url = None
        self.cookie_jar = None

    async def _stop(self, *args, **kwargs):
        print('stop')

    def _get_proxied_url(self, request):
        # [scheme:]//[user[:password]@]host[:port][/path][?query][#fragment]

        return URL.build(
            scheme=self.proxy_url.scheme or request.url.scheme,
            user=self.proxy_url.user or request.url.user,
            password=self.proxy_url.password or request.url.password,
            host=self.proxy_url.host or request.url.host,
            port=self.proxy_url.port or request.url.port,
            path=request.url.path,
            query=request.url.query,
            fragment=request.url.fragment,
        )

    def _set_proxy(self, proxy_url):
        self.proxy_url = URL(proxy_url)
        self.cookie_jar = CookieJar(unsafe=True)

    def run_forever(self, *args, **kwargs):
        return run_app(app=self.app, *args, **kwargs)

    async def handle_config_request(self, request):
        data = await request.post()

        if 'proxy-pass' in data:
            self._set_proxy(proxy_url=data['proxy-pass'])

        return Response(status=200)

    async def handle_frontend_request(self, request):
        rel_path = request.match_info['path']

        if rel_path.startswith('/'):
            rel_path = rel_path[1:]

        abs_path = os.path.join(FRONTEND_STATIC_ROOT, rel_path)

        if not os.path.exists(abs_path):
            raise HTTPNotFound()

        if os.path.isdir(abs_path):
            index_path = os.path.join(abs_path, 'index.html')

            if os.path.exists(index_path):
                return FileResponse(path=index_path)

            raise HTTPNotFound()

        return FileResponse(path=abs_path)

    async def handle_websocket_client_connection(self, request, socket_pair):
        url = self._get_proxied_url(request)
        server_websocket = socket_pair[0]

        async with ClientSession() as client:
            async with client.ws_connect(url) as client_websocket:
                socket_pair[1] = client_websocket
                socket_pair[2].set_result(True)

                async for message in client_websocket:
                    if message.type == WSMsgType.TEXT:
                        try:
                            await server_websocket.send_str(message.data)

                        except ConnectionResetError:
                            break

                    elif message.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        break

    async def handle_websocket_proxy_request(self, request):
        websocket = WebSocketResponse()

        await websocket.prepare(request)

        socket_pair = [websocket, None, asyncio.Future()]

        asyncio.create_task(
            self.handle_websocket_client_connection(request, socket_pair)
        )

        await socket_pair[2]
        client_websocket = socket_pair[1]

        # main loop
        try:
            async for message in websocket:
                if message.type == WSMsgType.TEXT:
                    await client_websocket.send_str(message.data)

                elif message.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                    break

        except asyncio.CancelledError:
            pass

        except ConnectionResetError:
            pass

        finally:
            await websocket.close()

        return websocket

    async def handle_request(self, request):
        if not self.proxy_url:
            return Response(status=502)

        # websocket requests
        if (request.method == 'GET' and
                request.headers.get('upgrade', '').lower() == 'websocket'):

            return await self.handle_websocket_proxy_request(request)

        url = self._get_proxied_url(request)

        # GET / POST / HEAD requests
        async with ClientSession(cookie_jar=self.cookie_jar) as client:
            func = {
                'get': client.get,
                'post': client.post,
                'head': client.head,
            }[request.method.lower()]

            func_args = [url, ]
            func_kwargs = {}

            # header
            func_kwargs['headers'] = dict(request.headers)

            # post data
            if request.method == 'post':
                func_kwargs['data'] = request.data

            async with func(*func_args, **func_kwargs) as client_response:
                return Response(
                    headers=dict(client_response.headers),
                    status=client_response.status,
                    body=await client_response.text(),
                )


if __name__ == '__main__':

    # parse command line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=8081)

    args = parser.parse_args()

    # run frontend server
    FrontendServer().run_forever(host=args.host, port=args.port)
