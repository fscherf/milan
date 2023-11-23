from tempfile import TemporaryDirectory
import logging
import time

from milan.utils.reverse_proxy import ReverseProxy
from milan.utils.misc import retry, unique_id
from milan.utils.process import Process
from milan.cdp_client import CdpClient
from milan.browser import Browser
from milan.utils.url import URL


class CdpBrowser(Browser):
    def __init__(self, **kwargs):
        super().__init__()

        self.debug_port = kwargs.get('debug_port', 0)
        self.reverse_proxy_port = kwargs.get('reverse_proxy_port', None)

        self.user_data_dir = TemporaryDirectory()
        self.profile_id = unique_id()

        self.browser_command = self._get_browser_command(kwargs)
        self.browser_process = None
        self.cdp_client = None
        self.reverse_proxy = None

        try:
            self._start()

        except Exception:
            self.logger.exception('exception raised while starting up')
            self.stop()

    def _get_browser_command(self, kwargs):
        raise NotImplementedError()

    def _find_devtools_debug_port(self, stdout_line):
        prefix = 'DevTools listening on '

        # debug port was already found
        if self.debug_port > 0:
            return

        if not stdout_line.startswith(prefix):
            return

        # prefix found
        try:
            url_string = stdout_line[len(prefix):]
            url = URL(url_string)

            self.debug_port = int(url.port)

        except Exception:
            pass

        self.logger.debug(
            'devtools debug port is set to %s',
            self.debug_port,
        )

    def _start(self):

        # start browser process
        self.logger.debug('starting browser process')

        self.browser_process = Process(
            command=self.browser_command,
            on_stdout_line=self._find_devtools_debug_port,
            logger=logging.getLogger(f'{self.logger.name}.browser'),
        )

        # wait for devtools debug port to open
        if self.debug_port == 0:
            self.logger.debug('waiting for devtools debug port to open')

            @retry
            def wait_for_devtools_debug_port():
                if self.debug_port == 0:
                    raise RuntimeError('devtools debug port did not open')

            wait_for_devtools_debug_port()

        # setup reverse proxy
        if self.reverse_proxy_port:
            self.logger.debug('starting reverse proxy')

            self.reverse_proxy = ReverseProxy(
                port=self.reverse_proxy_port,
                remote_host='127.0.0.1',
                remote_port=self.debug_port,
                logger=logging.getLogger(f'{self.logger.name}.reverse-proxy'),
            )

        # HACK: prevent race conditions between non-headless chrome and X11
        if self.is_chrome() and '--headless' not in self.browser_command:
            self.logger.warning(
                'HACK: sleeping 1s before connecting to the debug port to prevent race conditions with X11',
            )

            time.sleep(1)

        # connect to debug port
        self.logger.debug('connecting to the browsers debug port')

        self.cdp_client = CdpClient(
            host='127.0.0.1',
            port=self.debug_port,
            event_router=self._event_router,
            logger=logging.getLogger(f'{self.logger.name}.cdp-client'),
        )

        # navigate to frontend
        self._navigate_browser(url=self._frontend_server.get_url())

        # finish
        self.logger.debug('browser started')

    def stop(self):
        self.logger.debug('stopping')

        super().stop()

        if self.cdp_client:
            self.cdp_client.stop()

        if self.browser_process:
            self.browser_process.stop()

        if self.reverse_proxy:
            self.reverse_proxy.stop()

    # browser hooks ###########################################################
    def _navigate_browser(self, url):
        future = self.await_browser_load(await_future=False)

        self.cdp_client.page_navigate(url=URL.normalize(url))

        future.result()

    def evaluate(self, expression):
        return self.cdp_client.runtime_evaluate(
            expression=expression,
            await_promise=True,
            repl_mode=False,
        )

    def resize(self, width, height):
        return self.cdp_client.emulation_set_device_metrics_override(
            width=width,
            height=height,
        )

    def screenshot(self, path, quality=100):
        return self.cdp_client.page_screenshot(
            path=path,
            quality=quality,
        )

    def start_video_capturing(
            self,
            output_path,
            fps=60,
            image_format='png',
            image_quality=100,
    ):

        if self.is_firefox():
            raise NotImplementedError(
                'CDP based video recording is not supported in firefox',
            )

        return self.cdp_client.start_video_capturing(
            output_path=output_path,
            fps=fps,
            image_format=image_format,
            image_quality=image_quality,
        )

    def stop_video_capturing(self):
        if self.is_firefox():
            raise NotImplementedError(
                'CDP based video recording is not supported in firefox',
            )

        return self.cdp_client.stop_video_capturing()
