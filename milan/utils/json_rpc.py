import concurrent
import functools
import threading
import logging
import queue
import json
import os

from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect

from milan.utils.misc import AtomicCounter, LazyString, pformat_dict

default_logger = logging.getLogger('milan.json-rpc')


class JsonRpcError(Exception):
    def __init__(self, *args, json_rpc_message=None, **kwargs):
        self.json_rpc_message = json_rpc_message


class JsonRpcStoppedError(JsonRpcError):
    pass


class JsonRpcTransport:
    def read_message(self):
        raise NotImplementedError

    def write_message(self, message):
        raise NotImplementedError

    def stop(self):
        pass


class JsonRpcMessage:
    def __init__(self, payload):
        self.payload = payload

        if isinstance(self.payload, str):
            self.payload = json.loads(self.payload)

    def __str__(self, trim=None):
        if trim is None:
            trim = 'MILAN_DEBUG' not in os.environ

        return (
            f"<JsonRpcMessage(type={self.type.upper()}, id={self.id!r}>\n"
            f"{pformat_dict(data=self.payload, indent=True, trim=trim)}\n"
            f"</JsonRpcMessage>"
        )

    def __repr__(self):
        return self.__str__(trim=False)

    @property
    def type(self):
        if 'error' in self.payload:
            return 'error'

        if 'result' in self.payload:
            return 'response'

        if 'method' in self.payload:
            if 'id' in self.payload:
                return 'request'

            else:
                return 'notification'

        raise JsonRpcError('invalid type')

    @property
    def id(self):
        return self.payload.get('id', None)

    @property
    def method(self):
        return self.payload.get('method', '')

    @property
    def params(self):
        return self.payload.get('params', {})

    @property
    def result(self):
        return self.payload.get('result', {})

    @property
    def error(self):
        return self.payload.get('error', {})

    @property
    def error_code(self):
        error = self.error

        return error.get('code', 0)

    @property
    def error_message(self):
        error = self.error

        return error.get('message', '')

    @property
    def error_data(self):
        error = self.error

        return error.get('data', {})

    @property
    def extra_properties(self):
        return {
            key: value
            for key, value in self.payload.items()
            if key not in ('id', 'method', 'params', 'result', 'error')
        }

    def serialize(self):
        try:
            return json.dumps(self.payload)

        except TypeError:
            raise JsonRpcError(
                'unable to encode payload to JSON: {self.payload!r}'
            )

    def get_lazy_string(self):
        return LazyString(
            obj=self,
            indent=True,
        )


class JsonRpcClient:
    """
    Implements client-side JSONRPC v1
    https://www.jsonrpc.org/specification_v1
    """

    def __init__(
            self,
            transport,
            worker_thread_count=2,
            on_stop=None,
            logger=default_logger,
    ):

        self.transport = transport
        self.worker_thread_count = worker_thread_count
        self.on_stop = on_stop
        self.logger = logger

        self._lock = threading.Lock()
        self._running = True
        self._message_id_counter = AtomicCounter()
        self._pending_requests = {}
        self._pending_notifications = {}
        self._notification_handler = {}

        # start receiver thread
        threading.Thread(
            target=self._handle_messages,

            # The message handling thread has to run as a daemon thread because
            # the `JsonRpcDebuggingPipeTransport` uses streams which use
            # `select.select`. In some cases, `select.select` blocks, even if
            # the fd is already closed.
            daemon=True,
        ).start()

        # start worker threads
        self._job_queue = queue.Queue()

        for worker_id in range(self.worker_thread_count):
            threading.Thread(
                target=self._handle_jobs,
                args=(worker_id, ),
            ).start()

    def __repr__(self):
        return f'<JsonRpcClient({self.transport=}, {self.worker_thread_count=})>'

    def _handle_messages(self):
        self.logger.debug('message worker started')

        while True:
            try:
                message = self.transport.read_message()

                try:
                    json_rpc_message = JsonRpcMessage(
                        payload=message,
                    )

                except JsonRpcError:
                    self.logger.exception(
                        'exception raised while reading message from transport',
                    )

                    continue

                self.logger.debug(
                    'JSON RPC Message received\n%s',
                    json_rpc_message.get_lazy_string(),
                )

                self._handle_json_rpc_message(
                    json_rpc_message=json_rpc_message,
                )

            except JsonRpcStoppedError:
                break

        self.logger.debug('message worker stopped')

    def _handle_json_rpc_message(self, json_rpc_message):

        # responses / errors
        if json_rpc_message.type in ('response', 'error'):
            future = self._pending_requests.pop(json_rpc_message.id, None)

            if future is None:
                self.logger.warning(
                    'received %s for unknown request id: %s',
                    json_rpc_message.type,
                    json_rpc_message.id,
                )

                return

            if future.done():
                return

            if json_rpc_message.type == 'response':
                future.set_result(result=json_rpc_message.result)

            else:
                future.set_exception(
                    exception=JsonRpcError(json_rpc_message=json_rpc_message),
                )

        # notifications
        elif json_rpc_message.type == 'notification':

            # subscriptions
            handlers = self._notification_handler.get(
                json_rpc_message.method,
                [],
            )

            for handler in handlers:
                self._job_queue.put(
                    functools.partial(handler, json_rpc_message),
                )

            # awaited notifications
            futures = self._pending_notifications.pop(
                json_rpc_message.method,
                [],
            )

            for future in futures:
                if future.done():
                    continue

                future.set_result(json_rpc_message)

            # nothing to do
            if not handlers and not futures:
                self.logger.debug(
                    'no handler found for %s',
                    json_rpc_message.method,
                )

    def _handle_jobs(self, worker_id):
        self.logger.debug('worker %s: started', worker_id)

        while self._running:
            self.logger.debug('worker %s: waiting for a job', worker_id)

            job = self._job_queue.get()

            if not job:
                continue

            self.logger.debug('worker %s: running %s', worker_id, job.func)

            try:
                job()

            except Exception:
                self.logger.exception(
                    'worker %s: exception raised while running %s',
                    worker_id,
                    job.func,
                )

        self.logger.debug('worker %s: stopped', worker_id)

    def stop(self):
        with self._lock:
            self._running = False

            # cancel all pending requests
            for future in self._pending_requests.values():
                if future.done():
                    continue

                future.set_exception(JsonRpcStoppedError())

            # cancel all pending notifications
            for future_list in self._pending_notifications.values():
                for future in future_list:
                    if future.done():
                        continue

                    future.set_exception(JsonRpcStoppedError())

            # stop all message worker
            for _ in range(self.worker_thread_count):
                self._job_queue.put(None)

        # stop transport
        try:
            self.transport.stop()

        except Exception:
            self.logger.exception(
                'exception raised while running %s',
                self.transport.stop,
            )

        # run on_stop hook
        if not self.on_stop:
            return

        self.logger.debug('running on_stop hook')

        try:
            self.on_stop(self)

        except Exception:
            self.logger.exception(
                'exception raised while running %s',
                self.on_stop,
            )

    def send_request(
            self,
            method,
            params=None,
            await_result=True,
            extra_properties=None,
    ):

        message_id = self._message_id_counter.increment()
        future = concurrent.futures.Future()

        json_rpc_message = JsonRpcMessage(
            payload={
                'id': message_id,
                'method': method,
                'params': params or {},
                **(extra_properties or {})
            },
        )

        self.logger.debug(
            'sending JSON RPC request\n%s',
            json_rpc_message.get_lazy_string(),
        )

        with self._lock:

            # the client was stopped while we were waiting for the lock
            if not self._running:
                raise JsonRpcStoppedError()

            self._pending_requests[message_id] = future

        try:
            self.transport.write_message(json_rpc_message.serialize())

        except JsonRpcStoppedError:
            self.stop()

            raise

        if not await_result:
            return future

        return future.result()

    def subscribe(self, methods, handler):
        if not isinstance(methods, (list, tuple)):
            methods = [methods]

        with self._lock:
            for method in methods:
                if method not in self._notification_handler:
                    self._notification_handler[method] = []

                self._notification_handler[method].append(handler)

        self.logger.debug('%s subscribed to %s', handler, methods)

    def await_notification(self, method, await_result=True):
        future = concurrent.futures.Future()

        with self._lock:
            if method not in self._pending_notifications:
                self._pending_notifications[method] = []

            self._pending_notifications[method].append(future)

        if not await_result:
            return future

        return future.result()


class JsonRpcWebsocketTransport(JsonRpcTransport):
    def __init__(self, url):
        self.url = url

        self._websocket = connect(self.url)

    def __repr__(self):
        return f'<JsonRpcWebsocketTransport({self.url=})>'

    def read_message(self):
        try:
            return self._websocket.recv()

        except (ConnectionClosedError, ConnectionClosedOK) as exception:
            raise JsonRpcStoppedError from exception

    def write_message(self, message):
        try:
            self._websocket.send(message)

        except (ConnectionClosedError, ConnectionClosedOK) as exception:
            raise JsonRpcStoppedError from exception

    def stop(self):
        self._websocket.close()


class JsonRpcDebuggingPipeTransport(JsonRpcTransport):
    def __init__(self, stream_in, stream_out, message_delimiter=b'\0'):
        self.stream_in = stream_in
        self.stream_out = stream_out
        self.message_delimiter = message_delimiter

    def __repr__(self):
        return f'<JsonRpcDebuggingPipeTransport({self.stream_in=}, {self.stream_out=})>'

    def read_message(self):
        try:
            binary_message = self.stream_out.read_message(
                delimiter=self.message_delimiter,
            )

            string_message = binary_message.decode()

            return string_message

        except OSError as exception:
            raise JsonRpcStoppedError from exception

    def write_message(self, message):
        try:
            binary_message = message.encode()

            binary_message += self.message_delimiter

            return self.stream_in.write(binary_message)

        except OSError as exception:
            raise JsonRpcStoppedError from exception

    def stop(self):
        self.stream_in.close()
        self.stream_out.close()
