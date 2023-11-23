import logging

from milan.frontend.commands import frontend_function
from milan.frontend.server import FrontendServer
from milan.event_router import EventRouter
from milan.utils.misc import unique_id
from milan.frontend import commands
from milan.utils.url import URL


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
        # TODO: add support for external sites besides 'localhost'
        # TODO: add support for cursor bootstrapping

        url = URL(url)

        # rewrite 'localhost' to '127.0.0.1' to prevent cookie settings loops
        # between the two origins (the frontend runs on '127.0.0.1')
        if url.host == 'localhost':
            url.host = '127.0.0.1'

        self.logger.debug('navigating frontend to %s', url)

        self.evaluate(
            expression=commands.gen_window_navigate_command(
                window_index=window,
                url=str(url),
                animation=self._get_animation(animation),
            ),
        )

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
