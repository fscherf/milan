import threading
import textwrap
import logging
import base64
import pprint
import urllib
import time
import copy
import uuid

import requests

http_default_logger = logging.getLogger('milan.http')


def unique_id():
    return str(uuid.uuid1())


def decode_base64(string):
    return base64.b64decode(string.encode('ascii'))


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


def http_get_request(url, logger=http_default_logger):
    request_id = unique_id()

    logger.debug('http request: GET %s" id=%s', url, request_id)

    response = requests.get(url=url)

    logger.debug(
        'http response: id=%s status=%s',
        request_id,
        response.status_code,
    )

    return response


def http_json_request(url, method='GET', logger=http_default_logger):
    request_id = unique_id()

    logger.debug('http request: "%s %s" id=%s', method, url, request_id)

    # method
    api_method = requests.get

    if method.lower() == 'post':
        api_method = requests.post

    # parse response
    response = api_method(url=url)

    if response.status_code != 200:
        raise RuntimeError(
            f'{method} {url} returned {response.status_code}'
        )

    data = response.json()

    logger.debug(
        'http response: id=%s\n%s',
        request_id,
        textwrap.indent(
            text=pprint.pformat(data),
            prefix='  ',
        ),
    )

    return data


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


class URL:
    @classmethod
    def normalize(cls, url_string):
        return str(cls(url_string))

    def __init__(self, url_string=''):
        url_string = str(url_string)

        if (not url_string.startswith('http') and
                not url_string.startswith('ws')):

            url_string = f'http://{url_string}'

        parse_result = urllib.parse.urlparse(url_string)

        self.protocol = parse_result.scheme
        self.host, self.port = (parse_result.netloc.split(':') + [''])[0:2]
        self.path = parse_result.path
        self.query = parse_result.query
        self.fragment = parse_result.fragment

    def __str__(self):
        url = f'{self.protocol}://{self.host}'

        if self.port:
            url = f'{url}:{self.port}'

        if self.path:
            path = self.path

            if path.startswith('/'):
                path = path[1:]

            url = f'{url}/{path}'

        if self.query:
            url = f'{url}?{self.query}'

        if self.fragment:
            url = f'{url}#{self.fragment}'

        return url

    def __repr__(self):
        return f'<URL({str(self)})>'

    @property
    def server(self):
        server = f'{self.protocol}://{self.host}'

        if self.port:
            server = f'{server}:{self.port}'

        return server
