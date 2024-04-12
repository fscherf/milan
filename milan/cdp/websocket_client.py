import logging
import time
import os

from milan.utils.json_rpc import JsonRpcClient, JsonRpcWebsocketTransport
from milan.utils.misc import decode_base64, retry, unique_id
from milan.utils.event_router import EventRouter
from milan.video_recorder import VideoRecorder
from milan.utils.http import HttpClient


class CdpWebsocketClient:
    """
    https://chromedevtools.github.io/devtools-protocol/
    """

    def __init__(
            self,
            loop,
            host,
            port,
            event_router=None,
            on_json_rpc_client_stop=None,
            logger=None,
    ):

        self.loop = loop
        self.host = host
        self.port = port
        self.event_router = event_router
        self.logger = logger

        self.video_recorder = VideoRecorder(
            logger=logging.getLogger(f'{self.logger.name}.video-recorder'),  # NOQA
        )

        self.on_json_rpc_client_stop = on_json_rpc_client_stop

        self.http_client = None
        self.json_rpc_client = None

        self._browser_info = {}
        self._top_frame_id = ''
        self._execution_contexts = {}

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

        # setup HttpClient
        self.http_client = HttpClient(
            loop=self.loop,
            logger=self.logger,
        )

        # connect to debug port
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
        self.json_rpc_transport = JsonRpcWebsocketTransport(
            loop=self.loop,
            url=self.get_websocket_url(),
        )

        self.json_rpc_client = JsonRpcClient(
            self.json_rpc_transport,
            worker_thread_count=2,
            on_stop=self.on_json_rpc_client_stop,
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
                'Runtime.executionContextCreated',
                'Runtime.executionContextDestroyed',
            ],
            handler=self._handle_runtime_execution_context_events,
        )

        self.json_rpc_client.subscribe(
            methods=[
                'Page.screencastFrame',
            ],
            handler=self._handle_screen_cast_frame,
        )

        # enable events
        self.page_enable()
        self.runtime_enable()

        # find top frame id
        self._top_frame_id = self._get_top_frame_id()

    def stop(self):
        self.logger.debug('stopping')

        self.video_recorder.stop()

        if self.http_client:
            self.http_client.stop()

        if self.json_rpc_client:
            self.json_rpc_client.stop()

    # helper
    def _get_top_frame_id(self):
        return self.page_get_frame_tree()['frameTree']['frame']['id']

    # REST API ################################################################
    def get_browser_info(self, refresh=False):
        if (not self._browser_info) or refresh:
            response_status, json_data = self.http_client.get(
                url=f'http://{self.host}:{self.port}/json/list',
                json_response=True,
            )

            for target_info in json_data:
                if target_info['type'] != 'page':
                    continue

                self._browser_info = target_info

                break

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

        response = self.json_rpc_client.send_request(
            method='Network.enable',
        )

        return response.result

    # runtime
    def runtime_enable(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-enable
        """

        response = self.json_rpc_client.send_request(
            method='Runtime.enable',
        )

        return response.result

    def runtime_evaluate(
            self,
            expression,
            await_promise=True,
            repl_mode=False,
    ):

        """
        https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-evaluate
        """

        response = self.json_rpc_client.send_request(
            method='Runtime.evaluate',
            params={
                'expression': expression,
                'awaitPromise': await_promise,
                'replMode': repl_mode,
                'contextId': self._execution_contexts[self._top_frame_id],
            },
        )

        return response.result

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

        return response.result

    def emulation_set_emulated_media(
            self,
            media='',
            prefers_color_scheme='light',
            prefers_reduced_motion='no-preference',
            forced_colors='none',
    ):

        """
        https://chromedevtools.github.io/devtools-protocol/tot/Emulation/#method-setEmulatedMedia
        """

        response = self.json_rpc_client.send_request(
            method='Emulation.setEmulatedMedia',
            params={
                'media': media,
                'features': [
                    {
                        'name': 'prefers-color-scheme',
                        'value': prefers_color_scheme,
                    },
                    {
                        'name': 'prefers-reduced-motion',
                        'value': prefers_reduced_motion,
                    },
                    {
                        'name': 'forced-colors',
                        'value': forced_colors,
                    },
                ],
            },
        )

        return response.result

    # page
    def page_enable(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-enable
        """

        response = self.json_rpc_client.send_request(method='Page.enable')

        return response.result

    def page_get_frame_tree(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-getFrameTree
        """

        response = self.json_rpc_client.send_request(
            method='Page.getFrameTree',
        )

        return response.result

    def page_navigate(self, url):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-navigate
        """

        response = self.json_rpc_client.send_request(
            method='Page.navigate',
            params={
                'url': url,
                'frameId': self._top_frame_id,
                'transitionType': 'link',
            },
        )

        return response.result

    def page_screenshot(self, path, quality=100):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot
        """

        image_format = os.path.splitext(path)[1][1:]

        response = self.json_rpc_client.send_request(
            method='Page.captureScreenshot',
            params={
                'format': image_format,
                'quality': quality,
            },
        )

        with open(path, 'wb+') as f:
            f.write(decode_base64(response.result['data']))

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

        response = self.json_rpc_client.send_request(
            method='Page.startScreencast',
            params=params,
        )

        return response.result

    def page_stop_screen_cast(self):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-stopScreencast
        """

        response = self.json_rpc_client.send_request(
            method='Page.stopScreencast',
        )

        return response.result

    def page_screen_cast_frame_ack(self, session_id):
        """
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-screencastFrameAck
        """

        response = self.json_rpc_client.send_request(
            method='Page.screencastFrameAck',
            params={
                'sessionId': session_id,
            },
        )

        return response.result

    # events ##################################################################
    def _handle_navigation_events(self, json_rpc_message):
        method = json_rpc_message.method

        if method == 'Page.loadEventFired':
            self.event_router.fire_event('browser_load')

        elif method in ('Page.frameNavigated', 'Page.navigatedWithinDocument'):
            self.event_router.fire_event('browser_navigated')

    def _handle_runtime_execution_context_events(self, json_rpc_message):
        method = json_rpc_message.method

        if method == 'Runtime.executionContextCreated':
            frame_id = json_rpc_message.params['context']['auxData']['frameId']
            context_id = json_rpc_message.params['context']['id']

            self._execution_contexts[frame_id] = context_id

        elif method == 'Runtime.executionContextDestroyed':
            context_id = json_rpc_message.params['executionContextId']

            for key, value in self._execution_contexts.items():
                if value == context_id:
                    self._execution_contexts.pop(key, None)

                    break

    # video capturing #########################################################
    def _handle_screen_cast_frame(self, json_rpc_message):
        timestamp = json_rpc_message.params['metadata']['timestamp']
        image_data = decode_base64(json_rpc_message.params['data'])

        self.page_screen_cast_frame_ack(
            session_id=json_rpc_message.params['sessionId'],
        )

        self.video_recorder.write_frame(
            timestamp=timestamp,
            image_data=image_data,
        )

    def start_video_capturing(
            self,
            output_path,
            width=0,
            height=0,
            fps=0,
            frame_dir=None,
            image_format='png',
            image_quality=100,
    ):

        self.logger.debug('start video capturing to %s', output_path)

        self.video_recorder.start(
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
            frame_dir=frame_dir,
        )

        self.page_start_screen_cast(
            image_format=image_format,
            image_quality=image_quality,
        )

    def stop_video_capturing(self):
        self.logger.debug('stoping video capture')

        self.video_recorder.stop()
        self.page_stop_screen_cast()
