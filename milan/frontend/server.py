import tempfile
import logging
import asyncio
import os

from aiohttp.abc import AbstractAccessLogger

from aiohttp.web import (
    HTTPNotFound,
    FileResponse,
    Application,
    AppRunner,
    TCPSite,
)

from milan.frontend.proxy import Proxy

FRONTEND_STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

default_logger = logging.getLogger('milan.frontend.server')
default_access_logger = logging.getLogger('milan.frontend.server.access')


def get_aiohttp_access_logger_class(logger=default_access_logger):
    class AiohttpAccessLogger(AbstractAccessLogger):
        def log(self, request, response, time):
            logger.debug(
                f'{request.remote} {request.method} {request.path} {response.status}',
            )

    return AiohttpAccessLogger


class FrontendServer:
    def __init__(
            self,
            loop,
            host='127.0.0.1',
            port=0,
            logger=default_logger,
            access_logger=default_access_logger,
            extra_static_dirs=None,
            background_dir=None,
    ):

        self.loop = loop
        self.logger = logger
        self.access_logger = access_logger

        self.temp_dir = None

        self.static_dirs = [
            *(extra_static_dirs or []),
            FRONTEND_STATIC_ROOT,
        ]

        if background_dir:
            self.temp_dir = tempfile.TemporaryDirectory()

            os.symlink(
                os.path.abspath(background_dir),
                os.path.join(self.temp_dir.name, 'background'),
            )

            self.static_dirs.insert(0, self.temp_dir.name)

        # setup aiohttp
        self.app = Application()
        self.proxy = Proxy(loop=self.loop)

        self.app.router.add_route(
            '*',
            '/_milan/frontend/{path:.*}',
            self._handle_static_request,
        )

        self.app.router.add_route(
            '*',
            '/{path:.*}',
            self.proxy.handle_request,
        )

        # start aiohttp
        async def start_aiohttp_app():
            self.app_runner = AppRunner(
                app=self.app,
                access_log_class=get_aiohttp_access_logger_class(
                    logger=self.access_logger,
                ),
            )

            await self.app_runner.setup()

            self.site = TCPSite(
                runner=self.app_runner,
                host=host,
                port=port,
                reuse_port=True,
            )

            await self.site.start()

        future = asyncio.run_coroutine_threadsafe(
            coro=start_aiohttp_app(),
            loop=self.loop,
        )

        return future.result()

    def stop(self):
        async def _stop():
            await self.proxy.stop()
            await self.site.stop()
            await self.app_runner.cleanup()

        concurrent_future = asyncio.run_coroutine_threadsafe(
            coro=_stop(),
            loop=self.loop,
        )

        return concurrent_future.result()

    def getsockname(self):
        return self.site._server.sockets[0].getsockname()

    def get_url(self):
        host, port = self.getsockname()

        return f'http://{host}:{port}'

    def get_frontend_url(self):
        return f'{self.get_url()}/_milan/frontend/'

    def get_test_application_url(self):
        return f'{self.get_url()}/_milan/frontend/test-application/'

    # static files ############################################################
    def get_static_abs_path(self, rel_path):
        if rel_path.startswith('/'):
            rel_path = rel_path[1:]

        for static_dir in self.static_dirs:
            abs_path = os.path.join(static_dir, rel_path)

            if not os.path.exists(abs_path):
                continue

            if os.path.isdir(abs_path):
                index_path = os.path.join(abs_path, 'index.html')

                if os.path.exists(index_path):
                    return index_path

                continue

            return abs_path

        return None

    async def _handle_static_request(self, request):
        rel_path = request.match_info['path']
        abs_path = self.get_static_abs_path(rel_path)

        if not abs_path:
            raise HTTPNotFound()

        return FileResponse(
            path=abs_path,
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            },
        )


if __name__ == '__main__':
    import argparse

    import simple_logging_setup
    import rlpython

    from milan.utils.background_loop import BackgroundLoop

    # parse command line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--static-dirs', nargs='+')
    parser.add_argument('--background-dir', default='')

    args = parser.parse_args()

    # setup logging
    simple_logging_setup.setup(
        level='debug',
        preset='cli',
    )

    # run frontend server
    background_loop = BackgroundLoop()

    frontend_server = FrontendServer(
        loop=background_loop.loop,
        host=args.host,
        port=args.port,
        extra_static_dirs=(args.static_dirs or []),
        background_dir=args.background_dir,
    )

    print(f'running on {frontend_server.get_frontend_url()}')

    # start interactive shell
    rlpython.embed()

    # shutdown
    frontend_server.stop()
    background_loop.stop()
