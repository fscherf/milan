from tempfile import TemporaryDirectory
import time
import os

from milan.cdp.websocket_client import CdpWebsocketClient
from milan.utils.background_loop import BackgroundLoop
from milan.utils.json_rpc import JsonRpcStoppedError
from milan.utils.event_router import EventRouter
from milan.frontend.server import FrontendServer
from milan.errors import BrowserStoppedError
from milan.utils.media import image_convert
from milan.utils.process import Process
from milan.utils.misc import retry
from milan.utils.url import URL

from milan.browser import (
    DEFAULT_VIDEO_CAPTURING_START_DELAY,
    DEFAULT_VIDEO_CAPTURING_STOP_DELAY,
    browser_function,
    Browser,
)


class CdpWebsocketBrowser(Browser):
    TRANSLATE_ERRORS = {
        JsonRpcStoppedError: BrowserStoppedError,
    }

    def __init__(
            self,
            *args,
            debug_port=0,
            user_data_dir='',
            background_dir='',
            background_url='background/index.html',
            watermark='',
            **kwargs,
    ):

        super().__init__(*args, **kwargs)

        self.debug_port = debug_port
        self.user_data_dir = user_data_dir
        self.kwargs = kwargs

        self._background_loop = None
        self._user_data_dir_temp_dir = None
        self.browser_command = []
        self.browser_process = None
        self.cdp_websocket_client = None
        self._frontend_server = None
        self._event_router = EventRouter()

        try:
            self._start(
                background_dir=background_dir,
                background_url=background_url,
                watermark=watermark,
            )

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

    def _start(self, background_dir, background_url, watermark=''):
        from milan import VERSION_STRING  # avoid circular imports

        if not watermark:
            watermark = f'Milan v{VERSION_STRING}'

        # start background loop
        self.logger.debug('starting background loop')

        self._background_loop = BackgroundLoop(
            logger=self._get_sub_logger('background-loop'),
        )

        # setup user-data-dir
        if not self.user_data_dir:
            self._user_data_dir_temp_dir = TemporaryDirectory()
            self.user_data_dir = self._user_data_dir_temp_dir.name

        # start browser process
        self.logger.debug('starting browser process')

        self.browser_command = self._get_browser_command(self.kwargs)

        self.browser_process = Process(
            command=self.browser_command,
            on_stdout_line=self._find_devtools_debug_port,
            on_stop=self._handle_browser_process_stop,
            logger=self._get_sub_logger('browser'),
        )

        # wait for devtools debug port to open
        if self.debug_port == 0:
            self.logger.debug('waiting for devtools debug port to open')

            @retry
            def wait_for_devtools_debug_port():
                if self.debug_port == 0:
                    raise RuntimeError('devtools debug port did not open')

            wait_for_devtools_debug_port()

        # HACK: prevent race conditions between non-headless chrome and X11
        if self.is_chrome() and not self.headless:
            self.logger.warning(
                'HACK: sleeping 1s before connecting to the debug port to prevent race conditions with X11',
            )

            time.sleep(1)

        # connect to debug port
        self.logger.debug('connecting to the browsers debug port')

        self.cdp_websocket_client = CdpWebsocketClient(
            loop=self._background_loop.loop,
            host='127.0.0.1',
            port=self.debug_port,
            event_router=self._event_router,
            on_json_rpc_client_stop=self._handle_json_rpc_client_stop,
            logger=self._get_sub_logger('cdp-client'),
        )

        # start frontend
        self._frontend_server = FrontendServer(
            loop=self._background_loop.loop,
            host='127.0.0.1',
            port=0,
            logger=self._get_sub_logger('frontend.server'),
            access_logger=self._get_sub_logger('frontend.server.access'),
            background_dir=background_dir,
        )

        # navigate to frontend
        self.reload_frontend()

        # set background
        self.logger.debug('setting background URL')

        self.set_background_url(background_url)

        # set watermark
        self.logger.debug('setting watermark')

        self.set_watermark(watermark)

        # finish
        self.logger.debug('browser started')

    def stop(self):
        self.logger.debug('stopping')

        self._error = BrowserStoppedError

        if self.cdp_websocket_client:
            self.cdp_websocket_client.stop()

        if self.browser_process:
            self.browser_process.stop()

        if self._frontend_server:
            self._frontend_server.stop()

        if self._background_loop:
            self._background_loop.stop()

        self.logger.debug('stopped')

    def is_chrome(self):
        return False

    def is_firefox(self):
        return False

    # browser hooks ###########################################################
    @browser_function
    def _browser_navigate(self, url):
        future = self.await_browser_load(await_future=False)

        self.cdp_websocket_client.page_navigate(url=URL.normalize(url))

        future.result()

    @browser_function
    def _browser_evaluate(self, expression):
        return self.cdp_websocket_client.runtime_evaluate(
            expression=expression,
            await_promise=True,
            repl_mode=False,
        )

    @browser_function
    def _browser_set_size(self, width, height):
        return self.cdp_websocket_client.emulation_set_device_metrics_override(
            width=width,
            height=height,
        )

    @browser_function
    def screenshot(
            self,
            output_path,
            quality=100,
            width=0,
            height=0,
    ):

        output_format = os.path.splitext(output_path)[1][1:]
        output_path_converted = ''

        if output_format not in ('jpeg', 'png', 'webp'):
            raise ValueError(f'invalid output format: {output_format}')

        if width or height:
            output_path_converted = output_path
            output_path = f'{output_path}.raw.{output_format}'

        self.cdp_websocket_client.page_screenshot(
            path=output_path,
            quality=quality,
        )

        if width or height:
            image_convert(
                input_path=output_path,
                output_path=output_path_converted,
                width=width,
                height=height,
                logger=self._get_sub_logger('ffmpeg.image-convert'),
            )

            os.unlink(output_path)

    @browser_function
    def start_video_capturing(
            self,
            output_path,
            delay=DEFAULT_VIDEO_CAPTURING_START_DELAY,
            width=0,
            height=0,
            fps=0,
            frame_dir=None,
            image_format='png',
            image_quality=100,
    ):

        if self.is_firefox():
            raise NotImplementedError(
                'CDP based video recording is not supported in firefox',
            )

        return_value = self.cdp_websocket_client.start_video_capturing(
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
            frame_dir=frame_dir,
            image_format=image_format,
            image_quality=image_quality,
        )

        if delay:
            time.sleep(delay)

        return return_value

    @browser_function
    def stop_video_capturing(
            self,
            delay=DEFAULT_VIDEO_CAPTURING_STOP_DELAY,
    ):

        if self.is_firefox():
            raise NotImplementedError(
                'CDP based video recording is not supported in firefox',
            )

        if delay:
            time.sleep(delay)

        # FIXME: add comment
        self.force_rerender()

        return self.cdp_websocket_client.stop_video_capturing()
