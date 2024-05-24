from tempfile import TemporaryDirectory
import queue
import os

from milan.utils.json_rpc import (
    JsonRpcDebuggingPipeTransport,
    JsonRpcStoppedError,
    JsonRpcTransport,
    JsonRpcClient,
)

from milan.frontend.commands import wrap_expression_into_function_declaration
from milan.utils.background_loop import BackgroundLoop
from milan.browser import Browser, browser_function
from milan.utils.misc import retry, decode_base64
from milan.frontend.server import FrontendServer
from milan.errors import BrowserStoppedError
from milan.executables import get_executable
from milan.utils.media import image_convert
from milan.utils.process import Process
from milan.utils.url import URL


class TargetJsonRpcTransport(JsonRpcTransport):
    def __init__(
            self,
            json_rpc_client,
            target_id,
            page_proxy_id,
    ):

        self._json_rpc_client = json_rpc_client
        self._target_id = target_id
        self._page_proxy_id = page_proxy_id

        self._message_queue = queue.Queue()

        self._json_rpc_client.subscribe(
            methods=[
                'Target.dispatchMessageFromTarget',
            ],
            handler=self._handle_target_notifications,
        )

    def _handle_target_notifications(self, json_rpc_message):
        self._message_queue.put(json_rpc_message.params['message'])

    def read_message(self):
        message = self._message_queue.get()

        if message is None:
            raise JsonRpcStoppedError()

        return message

    def write_message(self, message):
        self._json_rpc_client.send_request(
            method='Target.sendMessageToTarget',
            params={
                'message': message,
                'targetId': self._target_id,
            },
            extra_properties={
                'pageProxyId': self._page_proxy_id,
            },
            await_result=False,
        )

    def stop(self):
        self._message_queue.put(None)


class Webkit(Browser):
    def __init__(
            self,
            *args,
            animations=True,
            headless=True,
            executable=None,
            user_data_dir='',
            background_dir='',
            background_url='background/index.html',
            watermark='',
            **kwargs,
    ):

        super().__init__(animations=animations)

        self.executable = executable
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.kwargs = kwargs

        self._user_data_dir_temp_dir = None
        self._background_loop = None
        self._browser_process = None
        self._frontend_server = None
        self._json_rpc_client = None
        self._target_json_rpc_client = None

        try:
            self._start(
                background_dir=background_dir,
                background_url=background_url,
                watermark=watermark,
            )

        except Exception:
            self.logger.exception('exception raised while starting up')
            self.stop()

    # start ###################################################################
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

    def _playwright_webkit_cdp_start(self):
        self.logger.debug('run playwright webkit CDP setup')

        self._json_rpc_client.send_request(
            method='Playwright.enable',
        )

        # get browserContextId
        self._browser_context_id = self._json_rpc_client.send_request(
            method='Playwright.createContext',
        ).result['browserContextId']

        # get pageProxyId and targetId
        future = self._json_rpc_client.await_notification(
            method='Target.targetCreated',
            await_result=False,
        )

        self._page_proxy_id = self._json_rpc_client.send_request(
            method='Playwright.createPage',
            params={
                'browserContextId': self._browser_context_id,
            },
        ).result['pageProxyId']

        notification = future.result()

        self._target_id = notification.params['targetInfo']['targetId']

        # start target json rpc client
        self._target_json_rpc_transport = TargetJsonRpcTransport(
            json_rpc_client=self._json_rpc_client,
            target_id=self._target_id,
            page_proxy_id=self._page_proxy_id,
        )

        self._target_json_rpc_client = JsonRpcClient(
            transport=self._target_json_rpc_transport,
            on_stop=self._handle_json_rpc_client_stop,
            logger=self._get_sub_logger('target-json-rpc-client'),
        )

        # setup navigation events
        self._target_json_rpc_client.subscribe(
            methods=[
                'Page.loadEventFired',
                'Page.frameNavigated',
                'Page.navigatedWithinDocument',
            ],
            handler=self._handle_navigation_events,
        )

        # get frameId
        future = self._target_json_rpc_client.await_notification(
            method='Runtime.executionContextCreated',
            await_result=False,
        )

        self._target_json_rpc_client.send_request(method='Page.enable')
        self._target_json_rpc_client.send_request(method='Runtime.enable')

        notification = future.result()

        self._frame_id = notification.params['context']['frameId']

        # finish
        self.logger.debug('playwright webkit CDP setup done')

    def _start(self, background_dir, background_url, watermark=''):
        from milan import VERSION_STRING  # avoid circular imports

        if not watermark:
            watermark = f'Milan v{VERSION_STRING}'

        self.logger.debug('starting')

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
        if not self.executable:
            self.executable = get_executable('webkit')

        self.browser_command = [
            self.executable,
            '--headless' if self.headless else '',
            '--inspector-pipe',
            '--no-startup-window',
            f'--user-data-dir={self.user_data_dir}',
        ]

        self.logger.debug('starting browser process')

        self._browser_process = Process(
            command=self.browser_command,
            on_stop=self._handle_browser_process_stop,
            logger=self._get_sub_logger('browser'),
            open_fds=(3, 4),
        )

        # connect to debugging pipe
        self.logger.debug('connecting to debugging pipe')

        self._debugging_pipe_in = self._browser_process.get_writable_stream(3)
        self._debugging_pipe_out = self._browser_process.get_readable_stream(4)

        self._json_rpc_transport = JsonRpcDebuggingPipeTransport(
            stream_in=self._debugging_pipe_in,
            stream_out=self._debugging_pipe_out,
        )

        self._json_rpc_client = JsonRpcClient(
            transport=self._json_rpc_transport,
            on_stop=self._handle_json_rpc_client_stop,
            logger=self._get_sub_logger('json-rpc-client'),
        )

        # playwright CDP start
        self._playwright_webkit_cdp_start()

        # start frontend
        self.logger.debug('starting frontend server')

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
        self.logger.debug('successfully started')

    # stop ####################################################################
    def _playwright_webkit_cdp_stop(self):

        # close browser
        # We don't wait for webkit to respond to this request because in
        # some cases the browser target gets destroyed before the result
        # to the `Playwright.close` call was sent. In these cases
        # `JsonRpcClient.send_request` blocks forever.
        self._json_rpc_client.send_request(
            method='Playwright.close',
            await_result=False,
        )

    def stop(self):
        self.logger.debug('stopping')

        self._error = BrowserStoppedError

        # playwright CDP stop
        if self._json_rpc_client and self._target_json_rpc_client:
            self._playwright_webkit_cdp_stop()

        # stop json rpc clients
        self.logger.debug('stopping json rpc clients')

        if self._json_rpc_client:
            self._json_rpc_client.stop()

        if self._target_json_rpc_client:
            self._target_json_rpc_client.stop()

        # stop frontend
        self.logger.debug('stopping frontend server')

        if self._frontend_server:
            self._frontend_server.stop()

        # stop browser process
        self.logger.debug('stopping browser process')

        if self._browser_process:
            self._browser_process.stop()

        # stop background loop
        self.logger.debug('stopping background loop')

        if self._background_loop:
            self._background_loop.stop()

        # finish
        self.logger.debug('successfully stopped')

    # events ##################################################################
    def _handle_navigation_events(self, json_rpc_message):
        method = json_rpc_message.method

        if method == 'Page.loadEventFired':
            self._event_router.fire_event('browser_load')

        elif method in ('Page.frameNavigated', 'Page.navigatedWithinDocument'):
            self._event_router.fire_event('browser_navigated')

    # browser hooks ###########################################################
    @browser_function
    def _browser_navigate(self, url):
        future = self.await_browser_load(await_future=False)

        self._json_rpc_client.send_request(
            method='Playwright.navigate',
            params={
                'url': URL.normalize(url),
                'pageProxyId': self._page_proxy_id,
                'frameId': self._frame_id,
            },
        )

        future.result()

    @browser_function
    def _browser_evaluate(self, expression):

        # get objectId
        @retry
        def get_object_id():
            # the periodic retrying this seems to be necessary because the
            # `Page.loadEventFired` event seems to be sent by the browser
            # before the `window.milan` is fully set up

            return self._target_json_rpc_client.send_request(
                method='Runtime.evaluate',
                params={
                    'expression': 'window.milan',
                    'returnByValue': False,
                },
                await_result=True,
            ).result['result']['objectId']

        object_id = get_object_id()

        # we have to use `Runtime.callFunctionOn` here because
        # `Runtime.evaluate` seems not to implement `awaitPromise` correctly
        return self._target_json_rpc_client.send_request(
            method='Runtime.callFunctionOn',
            params={
                'objectId': object_id,
                'awaitPromise': True,
                'functionDeclaration':
                    wrap_expression_into_function_declaration(expression),
            },
            extra_properties={
                'pageProxyId': self._page_proxy_id,
            },
            await_result=True,
        ).result

    @browser_function
    def _browser_set_size(self, width, height):
        self._json_rpc_client.send_request(
            method='Emulation.setDeviceMetricsOverride',
            params={
                'width': int(width),
                'height': int(height),
                'fixedLayout': False,
            },
            extra_properties={
                'pageProxyId': self._page_proxy_id,
            },
        )

        # await resize
        @retry
        def await_size():
            # the periodic retrying this seems to be necessary because
            # playwright webkit does not send proper resize events

            size = self.get_size()

            if width != size['width'] or height != size['height']:
                raise RuntimeError(
                    f'browser did not resize to {width}x{height}',
                )

        await_size()

    @browser_function
    def screenshot(
            self,
            output_path,
            quality=100,
            width=0,
            height=0,
    ):

        output_name, output_format = os.path.splitext(output_path)
        output_format = output_format[1:]
        output_path_converted = ''

        if output_format not in ('jpeg', 'png', 'webp'):
            raise ValueError(f'invalid output format: {output_format}')

        if width or height or output_format != 'png':
            output_path_converted = f'{output_name}.{output_format}'
            output_path = f'{output_name}.raw.png'

        # get browser size
        size = self.get_size()

        # screenshot rect
        response = self._target_json_rpc_client.send_request(
            method='Page.snapshotRect',
            params={
                'coordinateSystem': 'Viewport',
                'x': 0,
                'y': 0,
                'width': size['width'],
                'height': size['height'],
            },
        )

        # decode image data
        data_url = response.result['dataURL']
        image_meta_data, image_base64_data = data_url.split(',', 1)
        image_data = decode_base64(image_base64_data)

        with open(output_path, 'wb') as file_handle:
            file_handle.write(image_data)

        # convert image
        if width or height or output_format != 'png':
            image_convert(
                input_path=output_path,
                output_path=output_path_converted,
                width=width,
                height=height,
                logger=self._get_sub_logger('ffmpeg.image-convert'),
            )

            os.unlink(output_path)
