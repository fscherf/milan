from concurrent.futures import ThreadPoolExecutor
import contextlib
import functools
import asyncio
import logging

from milan.frontend.commands import frontend_function
from milan.utils.event_router import EventRouter
from milan.utils.misc import unique_id
from milan.frontend import commands
from milan.utils.url import URL


def browser_function(func):
    @functools.wraps(func)
    def wrapper(browser, *args, **kwargs):

        # check if browser is already in an error state
        if browser._error:
            raise browser._error

        # run function
        try:
            return func(browser, *args, **kwargs)

        except Exception as exception:

            # check if exception can be translated to a more
            # high-level exception
            exception_type = type(exception)

            if exception_type in browser.TRANSLATE_ERRORS:
                raise browser.TRANSLATE_ERRORS[exception_type] from exception

            raise

    return wrapper


class BrowserContext:
    def __init__(
            self,
            browser_class,
            *args,
            loop=None,
            max_workers=2,
            **kwargs,
    ):

        self._browser_class = browser_class
        self._browser_args = args
        self._loop = loop
        self._max_workers = max_workers
        self._browser_kwargs = kwargs

        self._browser = None
        self._executor = None

    def _start_browser(self):
        self._browser = self._browser_class(
            *self._browser_args,
            **self._browser_kwargs,
        )

    def _stop_browser(self):
        self._browser.stop()

    def __getattr__(self, name):
        with contextlib.suppress(AttributeError):
            return super().__getattr__(name)

        attribute = getattr(self._browser, name)

        if not callable(attribute):
            return attribute

        async def shim(*args, **kwargs):
            return await self._loop.run_in_executor(
                executor=self._executor,
                func=attribute,
            )

        return shim

    # sync API
    def __enter__(self):
        self._start_browser()

        return self._browser

    def __exit__(self, type, value, traceback):
        self._stop_browser()

    # async API
    async def __aenter__(self):
        self._loop = self._loop or asyncio.get_running_loop()
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

        await self._loop.run_in_executor(
            executor=self._executor,
            func=self._start_browser,
        )

        return self

    async def __aexit__(self, type, value, traceback):
        await self._loop.run_in_executor(
            executor=self._executor,
            func=self._stop_browser,
        )


class Browser:
    TRANSLATE_ERRORS = {}

    @classmethod
    def start(cls, *args, **kwargs):
        return BrowserContext(cls, *args, **kwargs)

    def __init__(
            self,
            animations=True,
            short_selector_timeout=0.2,
            short_selector_timeout_max=1,
            selector_timeout=0.2,
            selector_timeout_max=3,
    ):

        self.animations = animations
        self.short_selector_timeout = short_selector_timeout
        self.short_selector_timeout_max = short_selector_timeout_max
        self.selector_timeout = selector_timeout
        self.selector_timeout_max = selector_timeout_max

        self.id = unique_id()

        self.logger = logging.getLogger(
            f'milan.{self.__class__.__name__.lower()}.{self.id}',
        )

        self._event_router = EventRouter()
        self._error = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(id={self.id})>'

    def _get_sub_logger(self, name):
        return logging.getLogger(f'{self.logger.name}.{name}')

    def _get_animations(self, local_override):
        if local_override is not None:
            return local_override

        return self.animations

    def _get_short_selector_timeout(self, local_override):
        if local_override is not None:
            return local_override

        return self.short_selector_timeout

    def _get_short_selector_timeout_max(self, local_override):
        if local_override is not None:
            return local_override

        return self.short_selector_timeout_max

    def _get_selector_timeout(self, local_override):
        if local_override is not None:
            return local_override

        return self.selector_timeout

    def _get_selector_timeout_max(self, local_override):
        if local_override is not None:
            return local_override

        return self.selector_timeout_max

    # events ##################################################################
    @browser_function
    def await_browser_load(self, timeout=None, await_future=True):
        return self._event_router.await_event(
            name='browser_load',
            timeout=timeout,
            await_future=await_future,
        )

    @browser_function
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
    @browser_function
    def get_size(self):
        return self.evaluate(
            expression=commands.gen_window_manager_get_size_command(),
        )

    @frontend_function
    @browser_function
    def get_window_count(self):
        return self.evaluate(
            expression=commands.gen_window_manager_get_window_count_command(),
        )

    @frontend_function
    @browser_function
    def split(self):
        self.logger.info('splitting window')

        return self.evaluate(
            expression=commands.gen_window_manager_split_command(),
        )

    # cursor
    @frontend_function
    @browser_function
    def show_cursor(self):
        self.logger.info('showing cursor')

        return self.evaluate(
            expression=commands.gen_cursor_show_command(),
        )

    @frontend_function
    @browser_function
    def hide_cursor(self):
        self.logger.info('hiding cursor')

        return self.evaluate(
            expression=commands.gen_cursor_hide_command(),
        )

    @frontend_function
    @browser_function
    def cursor_is_visible(self):
        return self.evaluate(
            expression=commands.gen_cursor_is_visible_command(),
        )

    @frontend_function
    @browser_function
    def move_cursor(
            self,
            x=0,
            y=0,
            animation=None,
    ):

        self.logger.info('moving cursor to x=%s y=%s', x, y)

        return self.evaluate(
            expression=commands.gen_cursor_move_to_command(
                x=float(x),
                y=float(y),
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def move_cursor_to_home(self, animation=None):
        self.logger.info('moving cursor to home')

        return self.evaluate(
            expression=commands.gen_cursor_move_to_home_command(
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def get_cursor_position(self):
        return self.evaluate(
            expression=commands.gen_cursor_get_position_command(),
        )

    # window
    @frontend_function
    @browser_function
    def reload(self, window=0, animation=None):
        self.logger.info('reloading window %s', window)

        return self.evaluate(
            expression=commands.gen_window_reload_command(
                window_index=window,
                animation=self._get_animations(animation),
            ),
        )

    # window
    @frontend_function
    @browser_function
    def navigate_back(self, window=0, animation=None):
        self.logger.info('navigating window %s back', window)

        return self.evaluate(
            expression=commands.gen_window_navigate_back_command(
                window_index=window,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def navigate_forward(self, window=0, animation=None):
        self.logger.info('navigating window %s forward', window)

        return self.evaluate(
            expression=commands.gen_window_navigate_forward_command(
                window_index=window,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def get_fullscreen(self, window=0):
        return self.evaluate(
            expression=commands.gen_window_get_fullscreen_command(
                window_index=window,
            ),
        )

    @frontend_function
    @browser_function
    def set_fullscreen(self, window=0, fullscreen=True):
        self.logger.info(
            '%s fullscreen for window %s',
            'enabling' if fullscreen else 'disabling',
            window,
        )

        return self.evaluate(
            expression=commands.gen_window_set_fullscreen_command(
                window_index=window,
                fullscreen=fullscreen,
            ),
        )

    # window: selectors
    @frontend_function
    @browser_function
    def await_load(self, window=0, url=''):
        raise NotImplementedError()

    @frontend_function
    @browser_function
    def element_exists(
            self,
            selector,
            timeout=None,
            timeout_max=None,
            window=0,
    ):

        timeout = self._get_short_selector_timeout(timeout)
        timeout_max = self._get_short_selector_timeout_max(timeout_max)

        self.logger.info(
            "checking if element with selector '%s' in window %s exists with a timeout of %ss",  # NOQA
            selector,
            window,
            timeout_max,
        )

        _element_exists = self.evaluate(
            expression=commands.gen_window_element_exists_command(
                window_index=window,
                selector=selector,
                timeout=timeout,
                timeout_max=timeout_max,
            ),
        )

        self.logger.info(
            "element with selector '%s' %s in window %s",
            selector,
            'exists' if _element_exists else 'does not exist',
            window,
        )

        return _element_exists

    @frontend_function
    @browser_function
    def await_element(
            self,
            selector,
            timeout=None,
            timeout_max=None,
            window=0,
    ):

        timeout = self._get_selector_timeout(timeout)
        timeout_max = self._get_selector_timeout_max(timeout_max)

        self.logger.info(
            "waiting for element with selector '%s' in window %s with a timeout of %ss",  # NOQA
            selector,
            window,
            timeout_max,
        )

        return self.evaluate(
            expression=commands.gen_window_await_element_command(
                window_index=window,
                selector=selector,
                timeout=timeout,
                timeout_max=timeout_max,
            ),
        )

    @frontend_function
    @browser_function
    def await_text(
            self,
            selector,
            text,
            timeout=None,
            timeout_max=None,
            window=0,
    ):

        timeout = self._get_selector_timeout(timeout)
        timeout_max = self._get_selector_timeout_max(timeout_max)

        self.logger.info(
            "waiting for element with selector '%s' to contain '%s' in window %s with a timeout of %ss",  # NOQA
            selector,
            text,
            window,
            timeout_max,
        )

        return self.evaluate(
            expression=commands.gen_window_await_text_command(
                window_index=window,
                selector=selector,
                text=text,
                timeout=timeout,
                timeout_max=timeout_max,
            ),
        )

    # window: user input
    @frontend_function
    @browser_function
    def click(
            self,
            selector,
            timeout=None,
            timeout_max=None,
            animation=None,
            window=0,
    ):

        timeout = self._get_selector_timeout(timeout)
        timeout_max = self._get_selector_timeout_max(timeout_max)

        self.logger.info(
            "clicking on element with selector '%s' in window %s with a timeout of %ss",  # NOQA
            selector,
            window,
            timeout_max,
        )

        return self.evaluate(
            expression=commands.gen_window_click_command(
                window_index=window,
                selector=selector,
                timeout=timeout,
                timeout_max=timeout_max,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def fill(
            self,
            selector,
            value,
            timeout=None,
            timeout_max=None,
            animation=None,
            window=0,
    ):

        timeout = self._get_selector_timeout(timeout)
        timeout_max = self._get_selector_timeout_max(timeout_max)

        self.logger.info(
            "filling value '%s' into an element with selector '%s' in window %s with a timeout of %ss",  # NOQA
            value,
            selector,
            window,
            timeout_max,
        )

        return self.evaluate(
            expression=commands.gen_window_fill_command(
                window_index=window,
                selector=selector,
                value=value,
                timeout=timeout,
                timeout_max=timeout_max,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def check(
            self,
            selector,
            value=True,
            timeout=None,
            timeout_max=None,
            animation=None,
            window=0,
    ):

        timeout = self._get_selector_timeout(timeout)
        timeout_max = self._get_selector_timeout_max(timeout_max)

        self.logger.info(
            "%s checkbox with selector '%s' in window %s with a timeout of %ss",  # NOQA
            'checking' if value else 'unchecking',
            selector,
            window,
            timeout_max,
        )

        return self.evaluate(
            expression=commands.gen_window_check_command(
                window_index=window,
                selector=selector,
                value=value,
                timeout=timeout,
                timeout_max=timeout_max,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def select(
            self,
            selector,
            value=None,
            index=None,
            label=None,
            timeout=None,
            timeout_max=None,
            window=0,
            animation=None,
    ):

        timeout = self._get_selector_timeout(timeout)
        timeout_max = self._get_selector_timeout_max(timeout_max)
        identifier = ''

        if value:
            identifier = f"value '{value}'"

        elif value:
            identifier = f"index '{index}'"

        elif label:
            identifier = f"label '{label}'"

        self.logger.info(
            "selecting option with %s in select with selector '%s' in window %s with a timeout of %ss",  # NOQA
            identifier,
            selector,
            window,
            timeout_max
        )

        return self.evaluate(
            expression=commands.gen_window_select_command(
                window_index=window,
                selector=selector,
                value=value,
                index=index,
                label=label,
                timeout=timeout,
                timeout_max=timeout_max,
                animation=self._get_animations(animation),
            ),
        )

    # navigation ##############################################################
    @browser_function
    @frontend_function
    def navigate(self, url, window=0, animation=None):
        # TODO: add support for external sites besides 'localhost'
        # TODO: add support for cursor bootstrapping

        url = URL(url)

        # rewrite 'localhost' to '127.0.0.1' to prevent cookie settings loops
        # between the two origins (the frontend runs on '127.0.0.1')
        if url.host == 'localhost':
            url.host = '127.0.0.1'

        self.logger.info('navigating frontend to %s', url)

        return self.evaluate(
            expression=commands.gen_window_navigate_command(
                window_index=window,
                url=str(url),
                animation=self._get_animations(animation),
            ),
        )

    def navigate_to_test_application(self, *args, **kwargs):
        return self.navigate(
            url=self._frontend_server.get_test_application_url(),
            *args,
            **kwargs,
        )

    @browser_function
    def reload_frontend(self):
        self.logger.info('loading frontend')

        self._navigate_browser(url=self._frontend_server.get_frontend_url())

    # hooks ###################################################################
    def stop(self):
        raise NotImplementedError()

    def set_color_scheme(self, color_scheme):
        raise NotImplementedError()

    @browser_function
    def _navigate_browser(self, url):
        raise NotImplementedError()

    @browser_function
    def resize(self, width=0, height=0):
        raise NotImplementedError()

    @browser_function
    def evaluate(self, expression):
        raise NotImplementedError()

    @browser_function
    def screenshot(self, path):
        raise NotImplementedError()

    @browser_function
    def start_video_capturing(self, path):
        raise NotImplementedError()

    @browser_function
    def stop_video_capturing(self):
        raise NotImplementedError()
