import textwrap
import logging
import pprint

import requests

from milan.utils.misc import unique_id

http_default_logger = logging.getLogger('milan.http')


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
