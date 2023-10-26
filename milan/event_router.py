from concurrent.futures import Future
from threading import Lock


class EventRouter:
    def __init__(self):
        self._lock = Lock()

        self._pending_events = {
            # event_name: [future, ],
        }

        self._pending_states = {
            # state_name: {
            #     value: [future, ],
            # }
        }

        self._pending_state_changes = {
            # state_name: [future, ]
        }

        self._states = {
            # state_name: value,
        }

    # events
    def fire_event(self, name, payload=None, exception=None):
        futures = []

        with self._lock:
            if name not in self._pending_events:
                return

            futures.extend(self._pending_events[name])
            self._pending_events[name].clear()

        for future in futures:
            if exception:
                future.set_exception(exception=exception)

            else:
                future.set_result(result=payload)

    def await_event(self, name, timeout=None, await_future=True):
        future = Future()

        with self._lock:
            if name not in self._pending_events:
                self._pending_events[name] = []

            self._pending_events[name].append(future)

        if await_future:
            return future.result(timeout=timeout)

        return future

    # states
    def set_state(self, name, value):
        futures = []

        with self._lock:
            self._states[name] = value

            # specific states
            if (name in self._pending_states and
                    value in self._pending_states[name]):

                futures.extend(self._pending_states[name][value])
                self._pending_states[name][value].clear()

            # state changes
            if name in self._pending_state_changes:
                futures.extend(self._pending_state_changes)
                self._pending_state_changes.clear()

        for future in futures:
            future.set_result(value)

    def await_state_change(self, name, timeout=None, await_future=True):
        future = Future()

        with self._lock:
            if name not in self._pending_state_changes:
                self._pending_state_changes[name] = []

            self._pending_state_changes[name].append(future)

        if await_future:
            return future.result(timeout=timeout)

        return future

    def await_state(self, name, value, timeout=None, await_future=True):
        future = Future()

        with self._lock:
            if name in self._states and self._states[name] == value:
                future.set_result(value)

                return future

            if name not in self._pending_states:
                self._pending_states[name] = {}

            if value not in self._pending_states[name]:
                self._pending_states[name][value] = []

            self._pending_states[name][value].append(future)

        if await_future:
            return future.result(timeout=timeout)

        return future
