import concurrent
import functools
import threading
import logging
import queue
import json

from websockets.exceptions import ConnectionClosedError
from websockets.sync.client import connect

from milan.utils.misc import AtomicCounter, LazyString, pformat_dict

default_logger = logging.getLogger('milan.json-rpc')


class JsonRpcError(Exception):
    def __init__(self, *args, json_rpc_message=None, **kwargs):
        self.json_rpc_message = json_rpc_message


class JsonRpcStoppedError(JsonRpcError):
    pass


class JsonRpcMessage:
    def __init__(self, payload):
        self.payload = payload

        if isinstance(self.payload, str):
            self.payload = json.loads(self.payload)

    def __str__(self, trim=True):
        return (
            f"<JsonRpcMessage(type={self.type.upper()}, id={self.id!r}>\n"
            f"{pformat_dict(data=self.payload, indent=True, trim=True)}\n"
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

    def serialize(self):
        try:
            return json.dumps(self.payload)

        except TypeError:
            raise JsonRpcError(
                'unable to encode payload to JSON: {self.payload!r}'
            )

    def get_lazy_string(self):
        return LazyString(obj=self, indent=True)


class JsonRpcClient:
    """
    Implements client-side JSONRPC v1
    https://www.jsonrpc.org/specification_v1
    """

    def __init__(
            self,
            url,
            worker_thread_count=2,
            on_stop=None,
            logger=default_logger,
    ):

        self.url = url
        self.worker_thread_count = worker_thread_count
        self.on_stop = on_stop
        self.logger = logger

        self._lock = threading.Lock()
        self._running = True
        self._message_id_counter = AtomicCounter()
        self._pending_requests = {}
        self._notification_handler = {}

        # connect websocket
        self.logger.debug('connecting to %s', self.url)

        self._websocket = connect(self.url)

        # start receiver thread
        threading.Thread(target=self._handle_messages).start()

        # start worker threads
        self._job_queue = queue.Queue()

        for worker_id in range(self.worker_thread_count):
            threading.Thread(
                target=self._handle_jobs,
                args=(worker_id, ),
            ).start()

    def __repr__(self):
        return 'f<JsonRpcClient({self.url=}, {self.worker_thread_count=})>'

    def _handle_messages(self):
        self.logger.debug('message worker started')

        try:
            for websocket_message in self._websocket:
                try:
                    json_rpc_message = JsonRpcMessage(
                        payload=websocket_message,
                    )

                except JsonRpcError:
                    self.logger.exception(
                        'exception raised while reading websocket message',
                    )

                    continue

                self.logger.debug(
                    'JSON RPC Message received\n%s',
                    json_rpc_message.get_lazy_string(),
                )

                self._handle_json_rpc_message(
                    json_rpc_message=json_rpc_message,
                )

        except ConnectionClosedError:
            self.stop()

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

            if json_rpc_message.type == 'response':
                future.set_result(result=json_rpc_message.result)

            else:
                future.set_exception(
                    exception=JsonRpcError(json_rpc_message=json_rpc_message),
                )

        # notifications
        elif json_rpc_message.type == 'notification':
            handlers = self._notification_handler.get(
                json_rpc_message.method,
                [],
            )

            for handler in handlers:
                self._job_queue.put(
                    functools.partial(handler, json_rpc_message),
                )

            if not handlers:
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

            # stop all message worker
            for _ in range(self.worker_thread_count):
                self._job_queue.put(None)

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

    def send_request(self, method, params=None, await_result=True):
        message_id = self._message_id_counter.increment()
        future = concurrent.futures.Future()

        json_rpc_message = JsonRpcMessage(
            payload={
                'id': message_id,
                'method': method,
                'params': params or {},
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
            self._websocket.send(json_rpc_message.serialize())

        except ConnectionClosedError:
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
