from tempfile import TemporaryDirectory
import logging
import time
import os

from milan.utils.reverse_proxy import ReverseProxy
from milan.utils.misc import retry, unique_id
from milan.errors import BrowserStoppedError
from milan.utils.media import scale_image
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

    def _handle_browser_process_stop(self, process):
        # when the browser process stops before the browser.stop() was called
        # the browser object is regarded crashed

        if self._error != BrowserStoppedError:
            self.logger.error('browser process stopped unexpectedly')

            self._error = BrowserStoppedError

    def _handle_json_rpc_client_stop(self, json_rpc_client):
        # when the json rpc client stops before the browser.stop() was called
        # the browser object is regarded crashed

        if self._error != BrowserStoppedError:
            self.logger.error('json rpc client stopped unexpectedly')

            self._error = BrowserStoppedError

    def _start(self):

        # start browser process
        self.logger.debug('starting browser process')

        self.browser_process = Process(
            command=self.browser_command,
            on_stdout_line=self._find_devtools_debug_port,
            on_stop=self._handle_browser_process_stop,
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
            on_json_rpc_client_stop=self._handle_json_rpc_client_stop,
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

        self.logger.debug('stopped')

    # browser hooks ###########################################################
    def _navigate_browser(self, url):
        self._run_checks()

        future = self.await_browser_load(await_future=False)

        self.cdp_client.page_navigate(url=URL.normalize(url))

        future.result()

    def evaluate(self, expression):
        self._run_checks()

        return self.cdp_client.runtime_evaluate(
            expression=expression,
            await_promise=True,
            repl_mode=False,
        )

    def resize(self, width, height):
        self._run_checks()

        return self.cdp_client.emulation_set_device_metrics_override(
            width=width,
            height=height,
        )

    def screenshot(
            self,
            output_path,
            quality=100,
            width=0,
            height=0,
    ):

        self._run_checks()

        output_format = os.path.splitext(output_path)[1][1:]
        output_path_scaled = ''

        if output_format not in ('jpeg', 'png'):
            raise ValueError(f'invalid output format: {output_format}')

        if width or height:
            output_path_scaled = output_path
            output_path = f'{output_path}.unscaled.{output_format}'

        self.cdp_client.page_screenshot(
            path=output_path,
            quality=quality,
        )

        if width or height:
            scale_image(
                input_path=output_path,
                output_path=output_path_scaled,
                width=width,
                height=height,
                logger=self._get_sub_logger('ffmpeg.image-scale'),
            )

            os.unlink(output_path)

    def start_video_capturing(
            self,
            output_path,
            width=0,
            height=0,
            fps=0,
            image_format='png',
            image_quality=100,
    ):

        self._run_checks()

        if self.is_firefox():
            raise NotImplementedError(
                'CDP based video recording is not supported in firefox',
            )

        return self.cdp_client.start_video_capturing(
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
            image_format=image_format,
            image_quality=image_quality,
        )

    def stop_video_capturing(self):
        self._run_checks()

        if self.is_firefox():
            raise NotImplementedError(
                'CDP based video recording is not supported in firefox',
            )

        return self.cdp_client.stop_video_capturing()
