import logging
import time
import os

from milan.utils.misc import decode_base64, retry, unique_id
from milan.ffmpeg_video_recorder import FfmpegVideoRecorder
from milan.utils.event_router import EventRouter
from milan.utils.http import http_json_request
from milan.json_rpc import JsonRpcClient


class CdpClient:
    """
    https://chromedevtools.github.io/devtools-protocol/
    """

    def __init__(self, host, port, event_router=None, logger=None):
        self.host = host
        self.port = port
        self.event_router = event_router
        self.logger = logger

        self.ffmpeg_video_recorder = FfmpegVideoRecorder(
            logger=logging.getLogger(f'{self.logger.name}.ffmpeg-video-recorder'),  # NOQA
        )

        self.json_rpc_client = None

        self._browser_info = {}

        if not self.logger:
            self.logger = logging.getLogger(f'milan.cdp-client.{unique_id()}')

        if not self.event_router:
            self.event_router = EventRouter()

        try:
            self._start()

        except Exception:
            self.logger.exception(
                f'exception raised while connecting to {self.browser_id} debug port. stopping',  # NOQA
            )

            self.stop()

    def _start(self):

        @retry
        def wait_for_browser_info():
            self.logger.debug(
                'trying to connecting to %s:%s',
                self.host,
                self.port,
            )

            self.get_browser_info(refresh=True)

        wait_for_browser_info()

        self.logger.debug(
            'connected to browsers debug port\n'
            '  debugger frontend url: %s\n'
            '  debugger websocket url: %s',
            self.get_frontend_url(),
            self.get_websocket_url(),
        )

        # setup JsonRpcClient
        self.json_rpc_client = JsonRpcClient(
            url=self.get_websocket_url(),
            worker_thread_count=2,
            logger=logging.getLogger(f'{self.logger.name}.json-rpc'),
        )

        self.json_rpc_client.subscribe(
            methods=[
                'Page.loadEventFired',
                'Page.frameNavigated',
                'Page.navigatedWithinDocument',
            ],
            handler=self._handle_navigation_events,
        )

        self.json_rpc_client.subscribe(
            methods=[
                'Page.screencastFrame',
            ],
            handler=self._handle_screen_cast_frame,
        )

        # enable events
        self.page_enable()

    def stop(self):
        self.logger.debug('stopping')

        self.ffmpeg_video_recorder.stop()

        if self.json_rpc_client:
            self.json_rpc_client.stop()

    # REST API ################################################################
    def get_browser_info(self, refresh=False):
        if (not self._browser_info) or refresh:
            self._browser_info = http_json_request(
                url=f'http://{self.host}:{self.port}/json/list',
            )[0]

        return self._browser_info

    def get_frontend_url(self):
        url = self.get_browser_info()['devtoolsFrontendUrl']

        if not url:
            return '[NONE]'

        if url.startswith('/'):
            url = url[1:]

        return f'http://{self.host}:{self.port}/{url}'

    def get_websocket_url(self):
        return self.get_browser_info()['webSocketDebuggerUrl']

    # RPC requests ############################################################
    # network
    def network_enable(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Network/#method-enable
        """

        return self.json_rpc_client.send_request(method='Network.enable')

    # runtime
    def runtime_enable(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-enable
        """

        return self.json_rpc_client.send_request(method='Runtime.enable')

    def runtime_evaluate(
            self,
            expression,
            await_promise=True,
            repl_mode=False,
    ):

        """
        https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-evaluate
        """

        return self.json_rpc_client.send_request(
            method='Runtime.evaluate',
            params={
                'expression': expression,
                'awaitPromise': await_promise,
                'replMode': repl_mode,
            },
        )

    # emulation
    def emulation_set_device_metrics_override(
            self,
            width,
            height,
            scale_factor=0,
            mobile=False,
    ):

        """
        https://chromedevtools.github.io/devtools-protocol/tot/Emulation/#method-setDeviceMetricsOverride
        """

        response = self.json_rpc_client.send_request(
            method='Emulation.setDeviceMetricsOverride',
            params={
                'width': width,
                'height': height,
                'deviceScaleFactor': scale_factor,
                'mobile': mobile,
            },
        )

        time.sleep(1)  # FIXME: wait for resize

        return response

    # page
    def page_enable(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-enable
        """

        return self.json_rpc_client.send_request(method='Page.enable')

    def page_get_frame_tree(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-getFrameTree
        """

        return self.json_rpc_client.send_request(method='Page.getFrameTree')

    def page_navigate(self, url):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-navigate
        """

        frame_id = self.page_get_frame_tree()['frameTree']['frame']['id']

        return self.json_rpc_client.send_request(
            method='Page.navigate',
            params={
                'url': url,
                'frameId': frame_id,
                'transitionType': 'link',
            },
        )

    def page_screenshot(self, path, quality=100):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot
        """

        image_format = os.path.splitext(path)[1][1:]

        data = self.json_rpc_client.send_request(
            method='Page.captureScreenshot',
            params={
                'format': image_format,
                'quality': quality,
            },
        )

        with open(path, 'wb+') as f:
            f.write(decode_base64(data['data']))

    def page_start_screen_cast(
            self,
            image_format='png',
            image_quality=100,
            max_width=None,
            max_height=None,
            every_nth_frame=None,
    ):

        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-startScreencast
        """

        params = {
            'format': image_format,
            'quality': image_quality,
        }

        # maxWidth, maxHeight and everyNthFrame are optional, but may not be
        # `None` or `undefined`. Chromium will respond with an error, stating
        # "Failed to deserialize params.maxWidth - BINDINGS: int32 ".
        if max_width is not None:
            params['maxWidth'] = max_width

        if max_height is not None:
            params['maxHeight'] = max_height

        if every_nth_frame is not None:
            params['everyNthFrame'] = every_nth_frame

        return self.json_rpc_client.send_request(
            method='Page.startScreencast',
            params=params,
        )

    def page_stop_screen_cast(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-stopScreencast
        """

        return self.json_rpc_client.send_request(
            method='Page.stopScreencast',
        )

    def page_screen_cast_frame_ack(self, session_id):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-screencastFrameAck
        """

        return self.json_rpc_client.send_request(
            method='Page.screencastFrameAck',
            params={
                'sessionId': session_id,
            },
        )

    # events ##################################################################
    def _handle_navigation_events(self, json_rpc_message):
        method = json_rpc_message.method

        if method == 'Page.loadEventFired':
            self.event_router.fire_event('browser_load')

        elif method in ('Page.frameNavigated', 'Page.navigatedWithinDocument'):
            self.event_router.fire_event('browser_navigated')

    # video capturing #########################################################
    def _handle_screen_cast_frame(self, json_rpc_message):
        image_data = decode_base64(json_rpc_message.params['data'])

        self.page_screen_cast_frame_ack(
            session_id=json_rpc_message.params['sessionId'],
        )

        self.ffmpeg_video_recorder.write_frame(image_data=image_data)

    def start_video_capturing(
            self,
            output_path,
            fps=60,
            image_format='png',
            image_quality=100,
    ):

        self.logger.debug('start video capturing to %s', output_path)

        self.ffmpeg_video_recorder.start(
            output_path=output_path,
            fps=fps,
        )

        self.page_start_screen_cast(
            image_format=image_format,
            image_quality=image_quality,
        )

    def stop_video_capturing(self):
        self.logger.debug('stoping video capture')

        self.ffmpeg_video_recorder.stop()
        self.page_stop_screen_cast()
