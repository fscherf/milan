from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import logging
import os

FRONTEND_STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

logger = logging.getLogger('milan.frontend.server')


class NoCachingRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_STATIC_ROOT, **kwargs)

    def end_headers(self):

        # caching header
        self.send_header(
            'Cache-Control',
            'no-cache, no-store, must-revalidate',
        )

        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')

        # CORS header
        self.send_header('Access-Control-Allow-Origin', '*')

        super().end_headers()


class FrontendServer:
    def __init__(self, host='localhost', port=0):
        logger.debug('starting on %s:%s', host, port)

        self.http_server = ThreadingHTTPServer(
            (host, port),
            NoCachingRequestHandler,
        )

        Thread(
            target=self.http_server.serve_forever,
            daemon=True,
        ).start()

        logger.debug('running on %s', self.get_url())

    def get_url(self):
        host, port = self.http_server.server_address

        return f'http://{host}:{port}'

    def stop(self):
        logger.debug('stopping')

        self.http_server.server_close()


if __name__ == '__main__':
    from argparse import ArgumentParser

    # parse arguments
    parser = ArgumentParser()

    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--count', type=int, default=1)

    args = parser.parse_args()

    # start server
    instances = []

    for i in range(args.count):
        if args.port > 0:
            port = args.port + i

        else:
            port = args.port

        instance = FrontendServer(host=args.host, port=port)

        print(f'Running on {instance.get_url()}')

    print('(Press CTRL+C to quit)')

    # wait for stop
    while True:
        try:
            input()

        except KeyboardInterrupt:
            break

    # stop server instances
    print('\nstopping')

    for instance in instances:
        instance.stop()
