import logging

from milan.utils import URL, unique_id, http_get_request
from milan.frontend.server import FrontendServer
from milan.event_router import EventRouter
from milan.frontend import commands

from milan.frontend.commands import (
    frontend_function,
    get_cursor_source,
    gen_frontend_url,
)


class BrowserContext:
    def __init__(self, browser_class, *args, **kwargs):
        self.browser = browser_class(*args, **kwargs)

    def __enter__(self):
        return self.browser

    def __exit__(self, type, value, traceback):
        self.browser.stop()


class Browser:
    @classmethod
    def start(cls, *args, **kwargs):
        return BrowserContext(cls, *args, **kwargs)

    def __init__(self):
        self.id = unique_id()

        self.logger = logging.getLogger(
            f'milan.{self.__class__.__name__.lower()}.{self.id}',
        )

        self.animation = True

        self._frontend_server = FrontendServer(host='127.0.0.1', port=0)
        self._event_router = EventRouter()
        self._url = URL()
        self._frontend_connected = False

    def __repr__(self):
        return f'<{self.__class__.__name__}(id={self.id})>'

    def _get_animation(self, local_override):
        if local_override:
            return local_override

        return self.animation

    def stop(self):
        self._frontend_server.stop()

    def is_chrome(self):
        return False

    def is_firefox(self):
        return False

    # events ##################################################################
    def await_browser_load(self, timeout=None, await_future=True):
        return self._event_router.await_event(
            name='browser_load',
            timeout=timeout,
            await_future=await_future,
        )

    def await_browser_navigation(
            self,
            url=None,
            timeout=None,
            await_future=True,
    ):

        if url:
            return self._event_router.await_state(
                name='browser_url',
                value=URL.normalize(url),
                timeout=timeout,
                await_future=await_future,
            )

        return self._event_router.await_event(
            name='browser_navigation',
            timeout=timeout,
            await_future=await_future,
        )

    # frontend methods ########################################################
    # window manager
    @frontend_function
    def get_window_count(self):
        return self.evaluate(
            expression=commands.gen_window_manager_get_window_count_command(),
        )

    @frontend_function
    def split(self):
        return self.evaluate(
            expression=commands.gen_window_manager_split_command(),
        )

    # cursor
    @frontend_function
    def show_cursor(self):
        return self.evaluate(
            expression=commands.gen_cursor_show_command(),
        )

    @frontend_function
    def hide_cursor(self):
        return self.evaluate(
            expression=commands.gen_cursor_hide_command(),
        )

    @frontend_function
    def cursor_is_visible(self):
        raise NotImplementedError()

    @frontend_function
    def move_cursor(
            self,
            x=0,
            y=0,
            relative=False,
            home=False,
            animation=None,
    ):

        animation = self._get_animation(animation)

        raise NotImplementedError()

    @frontend_function
    def get_cursor_position(self):
        raise NotImplementedError()

    # window
    @frontend_function
    def reload(self, window=0):
        return self.evaluate(
            expression=commands.gen_window_reload_command(
                window_index=window,
            ),
        )

    @frontend_function
    def navigate_back(self, window=0):
        return self.evaluate(
            expression=commands.gen_window_navigate_back_command(
                window_index=window,
            ),
        )

    @frontend_function
    def navigate_forward(self, window=0):
        return self.evaluate(
            expression=commands.gen_window_navigate_forward_command(
                window_index=window,
            ),
        )

    # window: selectors
    @frontend_function
    def await_load(self, window=0, url=''):
        raise NotImplementedError()

    @frontend_function
    def await_element(self, selector, window=0):
        return self.evaluate(
            expression=commands.gen_window_await_element_command(
                window_index=window,
                selector=selector,
            ),
        )

    @frontend_function
    def await_text(self, selector, text, window=0):
        return self.evaluate(
            expression=commands.gen_window_await_text_command(
                window_index=window,
                selector=selector,
                text=text,
            ),
        )

    # window: user input
    @frontend_function
    def click(self, selector, window=0, animation=None):
        animation = self._get_animation(animation)

        return self.evaluate(
            expression=commands.gen_window_click_command(
                window_index=window,
                selector=selector,
                animation=animation,
            ),
        )

    @frontend_function
    def fill(self, selector, value, window=0, animation=None):
        animation = self._get_animation(animation)

        return self.evaluate(
            expression=commands.gen_window_fill_command(
                window_index=window,
                selector=selector,
                value=value,
                animation=animation,
            ),
        )

    @frontend_function
    def check(self, selector, value=True, window=0, animation=None):
        animation = self._get_animation(animation)

        return self.evaluate(
            expression=commands.gen_window_check_command(
                window_index=window,
                selector=selector,
                value=value,
                animation=animation,
            ),
        )

    @frontend_function
    def select(
            self,
            selector,
            value=None,
            index=None,
            label=None,
            window=0,
            animation=None,
    ):

        animation = self._get_animation(animation)

        return self.evaluate(
            expression=commands.gen_window_select_command(
                window_index=window,
                selector=selector,
                value=value,
                index=index,
                label=label,
                animation=animation,
            ),
        )

    # navigation ##############################################################
    def navigate(self, url, window=0, animation=None):
        url = URL(url)
        frontend_connected = self._frontend_connected
        initial_request = False

        # fill in previous URL attributes if necessary
        if not url.host:
            url.host = self._url.host

        if not url.port:
            url.port = self._url.port

        # rewrite localhost
        if url.host == 'localhost':
            url.host = '127.0.0.1'

        self.logger.debug('navigating to %s', url)

        # switching server
        if url.server != self._url.server:
            frontend_connected = False

            # check if frontend is available on the remote server
            self.logger.debug(
                'checking if frontend is available on %s',
                url.server,
            )

            remote_frontend_url = gen_frontend_url(base_url=str(url))

            try:
                response = http_get_request(
                    url=remote_frontend_url,
                    logger=self.logger,
                )

            except Exception:
                response = None

            # connect to the remote frontend of the server
            if (response and
                    response.status_code == 200 and
                    'set-cookie' not in response.headers):

                # FIXME: the 'set-cookie' check is necessary because of
                # Lonas session subsystem. Find better solution.

                self.logger.debug(
                    'connecting to remote frontend at %s',
                    remote_frontend_url,
                )

                self._navigate_browser(url=remote_frontend_url)
                frontend_connected = True
                initial_request = True

            # connect to local frontend
            else:
                local_frontend_url = self._frontend_server.get_url()

                self.logger.debug(
                    'connecting to local frontend at %s',
                    remote_frontend_url,
                )

                self._navigate_browser(url=local_frontend_url)
                frontend_connected = True
                initial_request = True

        # navigate frontend
        if frontend_connected:
            self.logger.debug('navigating frontend to %s', url)

            self.evaluate(
                expression=commands.gen_window_navigate_command(
                    window_index=window,
                    url=str(url),
                    animation=not initial_request,
                ),
            )

        # navigate browser
        else:
            self.logger.debug('navigating browser to %s', url)

            self._navigate_browser(url=str(url))

            # bootstrap cursor
            self.logger.debug('bootstraping cursor at %s', url)

            self.evaluate(expression=get_cursor_source())

        # update internal state
        self._url = url
        self._frontend_connected = frontend_connected

    # hooks ###################################################################
    def _navigate_browser(self, url):
        raise NotImplementedError()

    def resize(self, width=0, height=0):
        raise NotImplementedError()

    def evaluate(self, expression):
        raise NotImplementedError()

    def screenshot(self, path):
        raise NotImplementedError()

    def start_video_capture(self, path):
        raise NotImplementedError()

    def stop_video_capture(self):
        raise NotImplementedError()
