import asyncio

from yarl import URL

from aiohttp.web import WebSocketResponse, Response

from aiohttp import (
    ServerDisconnectedError,
    ClientConnectorError,
    ClientSession,
    CookieJar,
)

IGNORED_ERRORS = (
    ConnectionRefusedError,
    ConnectionResetError,
    asyncio.CancelledError,
    ServerDisconnectedError,
    ClientConnectorError,
)


class Proxy:
    def __init__(self, loop, url=''):
        self.loop = loop

        self._server_websockets = []
        self._client_websockets = []
        self._client_websocket_futures = []

        self.set_url(url=url, initial=True)

    async def stop(self):
        await self._stop_session()

    # session #################################################################
    async def _start_session(self):
        self._cookie_jar = CookieJar(
            loop=self.loop,
            unsafe=True,
        )

        self._client_session = ClientSession(
            cookie_jar=self._cookie_jar,
            loop=self.loop,
        )

    async def _stop_session(self):
        for websocket in self._server_websockets + self._client_websockets:
            await websocket.close()

        for future in self._client_websocket_futures:
            if future.done():
                continue

            future.set_result(None)

        await self._client_session.close()

    # URLs ####################################################################
    def get_url(self):
        return self._url

    def set_url(self, url, initial=False):
        async def _set_url():
            if not initial:
                await self._stop_session()

            await self._start_session()

            self._url = URL(url)

        concurrent_future = asyncio.run_coroutine_threadsafe(
            coro=_set_url(),
            loop=self.loop,
        )

        return concurrent_future.result()

    def _get_proxied_url(self, request):
        # [scheme:]//[user[:password]@]host[:port][/path][?query][#fragment]

        return URL.build(
            scheme=self._url.scheme or request.url.scheme,
            user=self._url.user or request.url.user,
            password=self._url.password or request.url.password,
            host=self._url.host or request.url.host,
            port=self._url.port or request.url.port,
            path=request.url.path,
            query=request.url.query,
            fragment=request.url.fragment,
        )

    def _get_reverse_proxied_url(self, url):
        # [scheme:]//[user[:password]@]host[:port][/path][?query][#fragment]

        url = URL(url)

        return URL.build(
            scheme='http',
            user=url.user or self._url.user,
            password=url.password or self._url.password,
            host='localhost',
            port=8080,
            path=url.path,
            query=url.query,
            fragment=url.fragment,
        )

    # request handling ########################################################
    # TODO: follow redirects
    # TODO: add loop protection

    def _bad_gateway(self):
        return Response(text='502: Bad Gateway', status=502)

    async def _handle_websocket_client_connection(
            self,
            request,
            server_websocket,
            client_websocket_future,
    ):

        url = self._get_proxied_url(request)

        # open client websocket connection
        try:
            client_websocket = await self._client_session.ws_connect(url)

        except IGNORED_ERRORS:
            await server_websocket.close()

            return

        client_websocket_future.set_result(client_websocket)
        self._client_websockets.append(client_websocket)

        # main loop
        try:
            async for message in client_websocket:
                await server_websocket.send_str(message.data)

        except IGNORED_ERRORS:
            pass

        finally:
            await client_websocket.close()
            await server_websocket.close()

            self._client_websockets.remove(client_websocket)

    async def _handle_websocket_proxy_request(self, request):

        # setup server websocket
        server_websocket = WebSocketResponse()

        await server_websocket.prepare(request)

        self._server_websockets.append(server_websocket)

        # setup client websocket
        client_websocket_future = asyncio.Future()
        self._client_websocket_futures.append(client_websocket_future)

        asyncio.create_task(
            coro=self._handle_websocket_client_connection(
                request=request,
                server_websocket=server_websocket,
                client_websocket_future=client_websocket_future,
            ),
        )

        client_websocket = await client_websocket_future

        self._client_websocket_futures.remove(client_websocket_future)

        if not client_websocket:
            return server_websocket

        # main loop
        try:
            async for message in server_websocket:
                await client_websocket.send_str(message.data)

        except IGNORED_ERRORS:
            pass

        finally:
            await server_websocket.close()

            self._server_websockets.remove(server_websocket)

        return server_websocket

    async def handle_request(self, request):
        if not self._url:
            return self._bad_gateway()

        # websocket requests
        if (request.method == 'GET' and
                request.headers.get('upgrade', '').lower() == 'websocket'):

            return await self._handle_websocket_proxy_request(request)

        # proxy url
        url = self._get_proxied_url(request)

        # GET / POST / HEAD requests
        func = {
            'get': self._client_session.get,
            'post': self._client_session.post,
            'head': self._client_session.head,
        }[request.method.lower()]

        func_args = [url, ]

        func_kwargs = {
            'allow_redirects': False,
        }

        # header
        request_headers = dict(request.headers)

        request_headers['host'] = f'{url.host}:{url.port}'

        func_kwargs['headers'] = request_headers

        # post data
        if request.method == 'post':
            func_kwargs['data'] = request.data

        try:
            client_response = await func(*func_args, **func_kwargs)

        except IGNORED_ERRORS:
            return self._bad_gateway()

        response_status = client_response.status
        response_headers = dict(client_response.headers)

        response_headers.pop('Content-Encoding', '')
        response_headers.pop('Content-Length', '')
        response_headers.pop('Transfer-Encoding', '')

        if client_response.status in (301, 302, 303):
            response_status = 302  # FIXME

            url = self._get_reverse_proxied_url(
                url=response_headers['Location'],
            )

            response_headers['Location'] = str(url)

        return Response(
            headers=response_headers,
            status=response_status,
            body=await client_response.read(),
        )
