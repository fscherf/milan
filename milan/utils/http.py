import textwrap
import asyncio
import logging
import pprint
import json

from aiohttp import ClientSession, CookieJar

from milan.utils.misc import unique_id

default_logger = logging.getLogger('milan.http')


class HttpClient:
    def __init__(self, loop, logger=default_logger):
        self.loop = loop
        self.logger = logger

        self.start()

    def _run_coroutine(self, coroutine):
        concurrent_future = asyncio.run_coroutine_threadsafe(
            coro=coroutine,
            loop=self.loop,
        )

        return concurrent_future.result()

    # sessions ################################################################
    def start(self):
        async def _start():
            self._cookie_jar = CookieJar(
                loop=self.loop,
                unsafe=True,
            )

            self._client_session = ClientSession(
                cookie_jar=self._cookie_jar,
                loop=self.loop,
            )

        return self._run_coroutine(_start())

    def stop(self):
        async def _stop():
            await self._client_session.close()

        return self._run_coroutine(_stop())

    # GET #####################################################################
    async def _request(self, method, url, json_response=False):
        request_id = unique_id()

        self.logger.debug(
            'http request: %s %s" id=%s',
            method,
            url,
            request_id,
        )

        response = await self._client_session.get(url=url)
        response_status = response.status
        response_text = await response.text()

        if json_response:
            response_text = json.loads(response_text)

            self.logger.debug(
                'http response: id=%s\n%s',
                request_id,
                textwrap.indent(
                    text=pprint.pformat(response_text),
                    prefix='  ',
                ),
            )

        else:
            self.logger.debug(
                'http response: id=%s status=%s',
                request_id,
                response_status,
            )

        return response_status, response_text

    def get(self, url, json_response=False):
        return self._run_coroutine(
            self._request(
                method='GET',
                url=url,
                json_response=json_response,
            ),
        )
