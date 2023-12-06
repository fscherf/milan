from concurrent.futures import ThreadPoolExecutor
import contextlib
import asyncio
import logging

from milan.frontend.commands import frontend_function
from milan.utils.event_router import EventRouter
from milan.frontend.server import FrontendServer
from milan.errors import BrowserStoppedError
from milan.utils.misc import unique_id
from milan.frontend import commands
from milan.utils.url import URL


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
    @classmethod
    def start(cls, *args, **kwargs):
        return BrowserContext(cls, *args, **kwargs)

    def __init__(self, animations=True):
        self.id = unique_id()

        self.logger = logging.getLogger(
            f'milan.{self.__class__.__name__.lower()}.{self.id}',
        )

        self.animations = animations

        self._frontend_server = FrontendServer(
            host='127.0.0.1',
            port=0,
            logger=self._get_sub_logger('frontend.server'),
        )

        self._event_router = EventRouter()
        self._error = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(id={self.id})>'

    def _get_sub_logger(self, name):
        return logging.getLogger(f'{self.logger.name}.{name}')

    def _get_animation(self, local_override):
        if local_override:
            return local_override

        return self.animations

    def _run_checks(self):

        # check if browser is in an error state
        if self._error:
            raise self._error

    def stop(self):
        self._error = BrowserStoppedError
        self._frontend_server.stop()

    def is_chrome(self):
        return False

    def is_firefox(self):
        return False

    # events ##################################################################
    def await_browser_load(self, timeout=None, await_future=True):
        self._run_checks()

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

        self._run_checks()

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
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_manager_get_window_count_command(),
        )

    @frontend_function
    def split(self):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_manager_split_command(),
        )

    # cursor
    @frontend_function
    def show_cursor(self):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_cursor_show_command(),
        )

    @frontend_function
    def hide_cursor(self):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_cursor_hide_command(),
        )

    @frontend_function
    def cursor_is_visible(self):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_cursor_is_visible_command(),
        )

    @frontend_function
    def move_cursor(
            self,
            x=0,
            y=0,
            animation=None,
    ):

        self._run_checks()

        return self.evaluate(
            expression=commands.gen_cursor_move_to_command(
                x=float(x),
                y=float(y),
                animation=self._get_animation(animation),
            ),
        )

    @frontend_function
    def move_cursor_to_home(self, animation=None):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_cursor_move_to_home_command(
                animation=self._get_animation(animation),
            ),
        )

    @frontend_function
    def get_cursor_position(self):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_cursor_get_position_command(),
        )

    # window
    @frontend_function
    def reload(self, window=0, animation=None):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_reload_command(
                window_index=window,
                animation=self._get_animation(animation),
            ),
        )

    # window
    @frontend_function
    def navigate_back(self, window=0, animation=None):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_navigate_back_command(
                window_index=window,
                animation=self._get_animation(animation),
            ),
        )

    @frontend_function
    def navigate_forward(self, window=0, animation=None):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_navigate_forward_command(
                window_index=window,
                animation=self._get_animation(animation),
            ),
        )

    @frontend_function
    def get_fullscreen(self, window=0):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_get_fullscreen_command(
                window_index=window,
            ),
        )

    @frontend_function
    def set_fullscreen(self, window=0, fullscreen=True):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_set_fullscreen_command(
                window_index=window,
                fullscreen=fullscreen,
            ),
        )

    # window: selectors
    @frontend_function
    def await_load(self, window=0, url=''):
        self._run_checks()

        raise NotImplementedError()

    @frontend_function
    def await_element(self, selector, window=0):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_await_element_command(
                window_index=window,
                selector=selector,
            ),
        )

    @frontend_function
    def await_text(self, selector, text, window=0):
        self._run_checks()

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
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_click_command(
                window_index=window,
                selector=selector,
                animation=self._get_animation(animation),
            ),
        )

    @frontend_function
    def fill(self, selector, value, window=0, animation=None):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_fill_command(
                window_index=window,
                selector=selector,
                value=value,
                animation=self._get_animation(animation),
            ),
        )

    @frontend_function
    def check(self, selector, value=True, window=0, animation=None):
        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_check_command(
                window_index=window,
                selector=selector,
                value=value,
                animation=self._get_animation(animation),
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

        self._run_checks()

        return self.evaluate(
            expression=commands.gen_window_select_command(
                window_index=window,
                selector=selector,
                value=value,
                index=index,
                label=label,
                animation=self._get_animation(animation),
            ),
        )

    # navigation ##############################################################
    def navigate(self, url, window=0, animation=None):
        # TODO: add support for external sites besides 'localhost'
        # TODO: add support for cursor bootstrapping

        self._run_checks()

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

    def navigate_to_test_application(self, *args, **kwargs):
        self._run_checks()

        return self.navigate(
            url=self._frontend_server.get_test_application_url(),
            *args,
            **kwargs,
        )

    def reload_frontend(self):
        self._navigate_browser(url=self._frontend_server.get_url())

    # hooks ###################################################################
    def _navigate_browser(self, url):
        self._run_checks()

        raise NotImplementedError()

    def resize(self, width=0, height=0):
        self._run_checks()

        raise NotImplementedError()

    def evaluate(self, expression):
        self._run_checks()

        raise NotImplementedError()

    def screenshot(self, path):
        self._run_checks()

        raise NotImplementedError()

    def start_video_capturing(self, path):
        self._run_checks()

        raise NotImplementedError()

    def stop_video_capturing(self):
        self._run_checks()

        raise NotImplementedError()
