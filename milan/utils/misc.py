import threading
import textwrap
import base64
import pprint
import time
import uuid
import copy


def unique_id():
    return str(uuid.uuid1())


def decode_base64(string):
    return base64.b64decode(string.encode('ascii'))


def compare_numbers(a, b, error_in_percent=0.01):
    """
    compare_numbers(24, 23.976023976023978) == True
    """

    min_value = a - a * error_in_percent
    max_value = a + a * error_in_percent

    return b >= min_value and b < max_value


def pformat_dict(data, indent=False, trim=False):
    def _trim(_data):
        for key, value in _data.items():

            # dict
            if isinstance(value, dict):
                _trim(value)

            # strings
            elif isinstance(value, str) and len(value) > 128:
                _data[key] = f'<String({len(value)})>'

        return _data

    if trim:
        data = _trim(copy.deepcopy(data))

    text = pprint.pformat(data, indent=2)

    if indent:
        text = textwrap.indent(
            text=text,
            prefix='  ',
        )

    return text


def retry(func, timeout=3.0, delay=0.2):
    def decorator():
        time_slept = 0

        while True:
            try:
                return func()

            except Exception:
                if time_slept > timeout:
                    raise

                time.sleep(delay)
                time_slept += delay

    return decorator


class LazyString:
    def __init__(self, obj, indent=False):
        self.obj = obj
        self.indent = indent

    def __str__(self):
        string = str(self.obj)

        if self.indent:
            string = textwrap.indent(
                text=string,
                prefix='  ',
            )

        return string


class AtomicCounter:
    def __init__(self, initial=0):
        self._lock = threading.Lock()

        self.set(value=initial)

    def __repr__(self):
        return f'<AtomicCounter({self.value})>'

    @property
    def value(self):
        return self._value

    def set(self, value):
        with self._lock:
            self._value = value

            return self._value

    def increment(self):
        with self._lock:
            self._value += 1

            return self._value
