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

DEFAULT_VIDEO_CAPTURING_START_DELAY = 1
DEFAULT_VIDEO_CAPTURING_STOP_DELAY = 2


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
            short_selector_retry_interval=0.2,
            short_selector_timeout=1,
            selector_retry_interval=0.2,
            selector_timeout=3,
    ):

        self.animations = animations
        self.short_selector_retry_interval = short_selector_retry_interval
        self.short_selector_timeout = short_selector_timeout
        self.selector_retry_interval = selector_retry_interval
        self.selector_timeout = selector_timeout

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

    def _get_short_selector_retry_interval(self, local_override):
        if local_override is not None:
            return local_override

        return self.short_selector_retry_interval

    def _get_short_selector_timeout(self, local_override):
        if local_override is not None:
            return local_override

        return self.short_selector_timeout

    def _get_selector_retry_interval(self, local_override):
        if local_override is not None:
            return local_override

        return self.selector_retry_interval

    def _get_selector_timeout(self, local_override):
        if local_override is not None:
            return local_override

        return self.selector_timeout

    # events ##################################################################
    @browser_function
    def await_browser_load(self, timeout=None, await_future=True):
        """
        Waits for the next JavaScript window load event (`window.onload`).

        `timeout` can be a positive number in seconds or `None`. If the is
        `None`, the default timeout is used.

        If `await_future` is true, the method blocks until the next event gets
        fired. If not, a `concurrent.futures.Future` object is returned that
        can be awaited outside the method.
        """

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

        """
        Waits for the next navigation event of the browser.

        If `url` is set, the browser waits until the given URL is present.

        `timeout` can be a positive number in seconds or `None`. If the is
        `None`, the default timeout is used.

        If `await_future` is true, the method blocks until the next event gets
        fired. If not, a `concurrent.futures.Future` object is returned that
        can be awaited outside the method.
        """

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
    @browser_function
    @frontend_function
    def evaluate(self, expression, window=0):
        """
        Evaluates the given JavaScript expression in the given window and
        returns the result.

        If `window` is set to `None`, the expression gets evaluated in the
        Milan frontend.
        """

        # evaluate in the real browser
        if window is None:
            return self._browser_evaluate(
                expression=commands.gen_evaluate_command(
                    expression=expression,
                ),
            )

        # evaluate in one of the windows
        return self._browser_evaluate(
            expression=commands.gen_window_evaluate_command(
                window_index=window,
                expression=expression,
            ),
        )

    @browser_function
    @frontend_function
    def add_style_sheet(self, text, window=0):
        """
        Adds a CSS stylesheet as text to the given window.
        """

        # add to browser
        if window is None:
            return self._browser_evaluate(
                expression=commands.gen_add_style_sheet_command(
                    text=text,
                ),
            )

        # add to window
        return self._browser_evaluate(
            expression=commands.gen_window_add_style_sheet_command(
                window_index=window,
                text=text,
            ),
        )

    # window manager
    @frontend_function
    @browser_function
    def get_size(self):
        """
        Returns the size of browser as dict.

        Example return value: `{'height': 720, 'width': 1_280}`
        """

        return self._browser_evaluate(
            expression=commands.gen_window_manager_get_size_command(),
        )

    @browser_function
    def set_size(self, width=0, height=0, even_values=True):
        """
        Resizes the browser to the given width and height.

        If `even_values` is set to true, odd values get rounded to even
        numbers. This is necessary for some FFmpeg filters.
        """

        if even_values:
            width = width + (width % 2)
            height = height + (height % 2)

        return self._browser_set_size(
            width=width,
            height=height,
        )

    @frontend_function
    @browser_function
    def get_window_count(self):
        """
        Returns the count of visible browser windows as integer.
        """

        return self._browser_evaluate(
            expression=commands.gen_window_manager_get_window_count_command(),
        )

    @frontend_function
    @browser_function
    def split(self):
        """
        Split the frontend clockwise into multiple windows.

        Max splits are three. So you can have four windows tops.
        """

        self.logger.info('splitting window')

        return self._browser_evaluate(
            expression=commands.gen_window_manager_split_command(),
        )

    @frontend_function
    @browser_function
    def set_background_url(self, url):
        """
        Sets the URL of the frontends background IFrame.

        Default is `/_milan/frontend/background/index.html`
        """

        return self._browser_evaluate(
            expression=commands.gen_window_manager_set_background_url_command(
                url=url,
            ),
        )

    @frontend_function
    @browser_function
    def set_watermark(self, text):
        """
        Sets the watermark of the frontends background.

        Default is `f'Milan v{milan.VERSION_STRING}'`
        """

        return self._browser_evaluate(
            expression=commands.gen_window_manager_set_watermark_command(
                text=text,
            ),
        )

    @frontend_function
    @browser_function
    def set_background(self, background):
        """
        Sets the background as CSS property.

        Example values:
          - `red`
          - `#FF0000`
          - `linear-gradient(0deg, rgba(34,193,195,1) 0%, rgba(253,187,45,1) 100%)`
        """

        return self._browser_evaluate(
            expression=commands.gen_window_manager_set_background_command(
                background=background,
            ),
        )

    @frontend_function
    @browser_function
    def force_rerender(self):
        return self._browser_evaluate(
            expression=commands.gen_window_manager_force_rerender_command(),
        )

    # cursor
    @frontend_function
    @browser_function
    def show_cursor(self):
        """
        Shows cursor.

        Has no effect if cursor is already visible.
        """

        self.logger.info('showing cursor')

        return self._browser_evaluate(
            expression=commands.gen_cursor_show_command(),
        )

    @frontend_function
    @browser_function
    def hide_cursor(self):
        """
        Hides cursor.

        Has no effect if cursor is already visible.
        """

        self.logger.info('hiding cursor')

        return self._browser_evaluate(
            expression=commands.gen_cursor_hide_command(),
        )

    @frontend_function
    @browser_function
    def cursor_is_visible(self):
        """
        Returns whether the cursor is visible as bool.
        """

        return self._browser_evaluate(
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

        """
        Moves cursor to given X and Y coordinates.

        If `animation` is set to true, the cursor is animated. If animation is
        set to `None` the `Browser.animation` property is used to determine if
        an animation should be played.
        """

        self.logger.info('moving cursor to x=%s y=%s', x, y)

        return self._browser_evaluate(
            expression=commands.gen_cursor_move_to_command(
                x=float(x),
                y=float(y),
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def move_cursor_to_home(self, animation=None):
        """
        Moves cursor to the middle of the screen.

        If `animation` is set to true, the cursor is animated. If animation is
        set to `None` the `Browser.animation` property is used to determine if
        an animation should be played.
        """

        self.logger.info('moving cursor to home')

        return self._browser_evaluate(
            expression=commands.gen_cursor_move_to_home_command(
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def get_cursor_position(self):
        """
        Returns the cursor position as dict.

        Example return value: `{'x': 640, 'y': 360}`
        """

        return self._browser_evaluate(
            expression=commands.gen_cursor_get_position_command(),
        )

    # window
    @frontend_function
    @browser_function
    def reload(self, window=0, animation=None):
        """
        Reloads the given window.

        If `animation` is set to true, an animation is played that uses the
        cursor to click on the reload button of the given window.

        If `animation` is set to `None` the `Browser.animation` property is
        used to determine if an animation should be played.
        """

        self.logger.info('reloading window %s', window)

        return self._browser_evaluate(
            expression=commands.gen_window_reload_command(
                window_index=window,
                animation=self._get_animations(animation),
            ),
        )

    # window
    @frontend_function
    @browser_function
    def navigate_back(self, window=0, animation=None):
        """
        Moves back in the history of the given window.

        If `animation` is set to true, an animation is played that uses the
        cursor to click on the back button of the given window.

        If `animation` is set to `None` the `Browser.animation` property is
        used to determine if an animation should be played.
        """

        self.logger.info('navigating window %s back', window)

        return self._browser_evaluate(
            expression=commands.gen_window_navigate_back_command(
                window_index=window,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def navigate_forward(self, window=0, animation=None):
        """
        Moves forward in the history of the given window.

        If `animation` is set to true, an animation is played that uses the
        cursor to click on the forward button of the given window.

        If `animation` is set to `None` the `Browser.animation` property is
        used to determine if an animation should be played.
        """

        self.logger.info('navigating window %s forward', window)

        return self._browser_evaluate(
            expression=commands.gen_window_navigate_forward_command(
                window_index=window,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def get_fullscreen(self, window=0):
        """
        Returns whether fullscreen is enabled for the given window as bool.        
        """

        return self._browser_evaluate(
            expression=commands.gen_window_get_fullscreen_command(
                window_index=window,
            ),
        )

    @frontend_function
    @browser_function
    def set_fullscreen(self, window=0, fullscreen=True, decorations=True):
        """
        Enables or disables fullscreen mode for the given window.

        If decorations is set to `False`, the window decorations are not shown
        and the page is in "true" fullscreen mode.
        """

        self.logger.info(
            '%s fullscreen for window %s %s decorations',
            'enabling' if fullscreen else 'disabling',
            window,
            'with' if decorations else 'without',
        )

        return self._browser_evaluate(
            expression=commands.gen_window_set_fullscreen_command(
                window_index=window,
                fullscreen=fullscreen,
                decorations=decorations,
            ),
        )

    @frontend_function
    @browser_function
    def _get_url(self, window=0):
        return self._browser_evaluate(
            expression=commands.gen_window_get_url_command(
                window_index=window,
            ),
        )

    def get_url(self, window=0):
        """
        Returns the URL of the given window as a `milan.utils.url.URL` object.
        """

        raw_url = self._get_url(window=window)

        return URL(raw_url)

    # window
    @frontend_function
    @browser_function
    def get_window_size(self, window=0):
        """
        Returns the size of the given window.

        Example return value: `{'height': 720, 'width': 1_280}`
        """

        return self._browser_evaluate(
            expression=commands.gen_window_get_size_command(
                window_index=window,
            ),
        )

    def set_window_size(self, width, height, window=0, even_values=True):
        """
        Sets the size of the given window.

        If `even_values` is set to true, odd values get rounded to even
        numbers. This is necessary for some FFmpeg filters.
        """

        current_browser_size = self.get_size()
        current_window_size = self.get_window_size()

        width = width + (
            current_browser_size['width'] - current_window_size['width'])

        height = height + (
            current_browser_size['height'] - current_window_size['height'])

        return self.set_size(
            width=width,
            height=height,
            even_values=even_values,
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
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Checks whether at least one element matching the given selector is
        present in the given window. The selector is reevaluated in the given
        retry interval until the timeout is reached.

        If `element_index` is set, a matching element with the given index
        is awaited.

        If `retry_interval` is set to `None` the
        `Browser.short_selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.short_selector_timeout` property is used instead.
        """

        retry_interval = self._get_short_selector_retry_interval(
            retry_interval,
        )

        timeout = self._get_short_selector_timeout(timeout)

        self.logger.info(
            "checking if element with selector '%s' #%s in window %s exists with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        _element_exists = self._browser_evaluate(
            expression=commands.gen_window_element_exists_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

        self.logger.info(
            "element with selector '%s' #%s %s in window %s",
            selector,
            element_index,
            'exists' if _element_exists else 'does not exist',
            window,
        )

        return _element_exists

    @frontend_function
    @browser_function
    def await_element(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector to be
        present in the given window. The selector is reevaluated in the given
        retry interval until the timeout is reached.
        If the timeout is reached, a `milan.FrontendError` is raised.

        If `element_index` is set, a matching element with the given index
        is awaited.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.

        !!! warning

            This method is deprecated and will be removed.

            Use `Browser.await_elements` instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "waiting for element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_await_element_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def await_elements(
            self,
            selectors,
            text='',
            present=True,
            match_all=True,
            count=None,
            index=None,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for one or more selectors to match one or more elements in the
        given window and returns the matching selectors. All selectors are
        reevaluated in the given retry interval until the timeout is reached.
        If the timeout is reached, a `milan.FrontendError` is raised.

        If `text` is set to a string, all matching elements must have the
        given text.

        If `present` is set to `False`, the method waits until no matching
        element is present.

        If `match_all` is set to `False` only one of the given selectors
        has to match.

        If `count` is set to a number, the method will wait until the amount
        of matching elements is the given number.

        If `element_index` is set to a number, the method will wait until a
        matching element with that index is present, regardless the overall
        count.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        if not isinstance(selectors, (list, tuple)):
            selectors = [selectors]

        self.logger.info(
            "waiting for %s with selectors '%s'%s in window %s to be %s [match_all=%s,timeout=%ss]",  # NOQA
            f'{count} element(s)' if count else 'element(s)',
            ','.join(selectors),
            f"and text '{text}'" if text else '',
            window,
            'present' if present else 'not present',
            match_all,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_await_elements_command(
                window_index=window,
                selectors=selectors,
                text=text,
                present=present,
                match_all=match_all,
                count=count,
                index=index,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def await_text(
            self,
            selector,
            text,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and text to
        be present in the given window. The selector is reevaluated in the
        given retry interval until the timeout is reached.
        If the timeout is reached, a `milan.FrontendError` is raised.

        If `element_index` is set, a matching element with the given index
        is awaited.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.

        !!! warning

            This method is deprecated and will be removed.

            Use `Browser.await_elements` instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "waiting for element with selector '%s' #%s to contain '%s' in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            text,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_await_text_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                text=text,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def get_element_count(
            self,
            selector,
            window=0,
    ):

        """
        Returns the amount of elements matching the given selector in the
        given window as integer.
        """

        self.logger.info(
            "counting elements with selector '%s' in window %s",
            selector,
            window,
        )

        element_count = self._browser_evaluate(
            expression=commands.gen_window_get_element_count_command(
                window_index=window,
                selector=selector,
            ),
        )

        return element_count

    @frontend_function
    @browser_function
    def get_html(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and returns
        its HTML as string.

        If `element_index` is set, a matching element with the given index
        is awaited and its value is returned.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "getting HTML from element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_get_html_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def set_html(
            self,
            selector,
            html,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and sets
        its HTML to the given string.

        If `element_index` is set, a matching element with the given index
        is awaited and its HTML is set.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "setting HTML in element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_set_html_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                html=html,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def get_text(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and returns
        its text as string.

        If `element_index` is set, a matching element with the given index
        is awaited and its value is returned.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "getting text from element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_get_text_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    def set_text(
            self,
            selector,
            text,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and sets
        its text to the given string.

        If `element_index` is set, a matching element with the given index
        is awaited and its text is set.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        return self.set_html(
            selector=selector,
            html=text,
            element_index=element_index,
            retry_interval=retry_interval,
            timeout=timeout,
            window=window,
        )

    @frontend_function
    @browser_function
    def get_attribute(
            self,
            selector,
            name,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and returns
        the attribute with the given name.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "getting attribute '%s' from element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            name,
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_get_attribute_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                name=name,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def get_attributes(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and returns
        all of its attributes as a dict.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are returned.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "getting attributes of element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_get_attributes_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def set_attributes(
            self,
            selector,
            attributes,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and sets
        the given attributes provided as a dict.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are set.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "setting attributes of element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_set_attributes_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                attributes=attributes,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    def set_attribute(
            self,
            selector,
            name,
            value,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and sets
        the given attribute name to the given value.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        return self.set_attributes(
            selector=selector,
            element_index=element_index,
            attributes={name: value},
            retry_interval=retry_interval,
            timeout=timeout,
            window=window,
        )

    @frontend_function
    @browser_function
    def remove_attributes(
            self,
            selector,
            names,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and removes
        the given attribute names.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "removing attributes '%s' of element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            names,
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_remove_attributes_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                names=names,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    def remove_attribute(
            self,
            selector,
            name,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and removes
        the given attribute name.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        return self.remove_attributes(
            selector=selector,
            names=[name],
            element_index=element_index,
            retry_interval=retry_interval,
            timeout=timeout,
            window=window,
        )

    def get_class_list(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and returns
        its CSS class list as a list of strings.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        class_list = self.get_attribute(
            selector=selector,
            element_index=element_index,
            name='class',
            retry_interval=retry_interval,
            timeout=timeout,
            window=window,
        ).split(' ')

        return [i for i in class_list if i]

    def set_class_list(
            self,
            selector,
            names,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and sets
        its CSS class list to the given list of strings.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        return self.set_attribute(
            selector=selector,
            name='class',
            value=' '.join(names),
            element_index=element_index,
            retry_interval=retry_interval,
            timeout=timeout,
            window=window,
        )

    def clear_class_list(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and clears
        its CSS class list.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        return self.set_attribute(
            selector=selector,
            name='class',
            value='',
            element_index=element_index,
            retry_interval=retry_interval,
            timeout=timeout,
            window=window,
        )

    @frontend_function
    @browser_function
    def class_list_add(
            self,
            selector,
            names,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and adds
        the given class to its CSS class list.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        if not isinstance(names, (list, tuple)):
            names = [names]

        self.logger.info(
            "adding classs '%s' to element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            repr(names),
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_class_list_add_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                names=names,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    @frontend_function
    @browser_function
    def class_list_remove(
            self,
            selector,
            names,
            element_index=0,
            retry_interval=None,
            timeout=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and removes
        the given class from its CSS class list.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        if not isinstance(names, (list, tuple)):
            names = [names]

        self.logger.info(
            "removing classes '%s' from element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            repr(names),
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_class_list_remove_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                names=names,
                retry_interval=retry_interval,
                timeout=timeout,
            ),
        )

    # window: user input
    @frontend_function
    @browser_function
    def click(
            self,
            selector,
            element_index=0,
            retry_interval=None,
            timeout=None,
            animation=None,
            window=0,
    ):

        """
        Waits for at least one element matching the given selector and fires
        a click event onto it.

        If `animation` is set to true, an animation using the cursor is played.
        If animation is set to `None` the `Browser.animation` property is used
        to determine if an animation should be played.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "clicking on element with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_click_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                retry_interval=retry_interval,
                timeout=timeout,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def fill(
            self,
            selector,
            value,
            element_index=0,
            retry_interval=None,
            timeout=None,
            animation=None,
            window=0,
    ):

        """
        Waits for at least one input matching the given selector and fills the
        given value into it.

        If `animation` is set to true, an animation using the cursor is played.
        If animation is set to `None` the `Browser.animation` property is used
        to determine if an animation should be played.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "filling value '%s' #%s into an element with selector '%s' in window %s with a timeout of %ss",  # NOQA
            value,
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_fill_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                value=value,
                retry_interval=retry_interval,
                timeout=timeout,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def check(
            self,
            selector,
            value=True,
            element_index=0,
            retry_interval=None,
            timeout=None,
            animation=None,
            window=0,
    ):

        """
        Waits for at least one checkbox matching the given selector and checks
        or unchecks it, depending on the given value.

        If `animation` is set to true, an animation using the cursor is played.
        If animation is set to `None` the `Browser.animation` property is used
        to determine if an animation should be played.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        self.logger.info(
            "%s checkbox with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            'checking' if value else 'unchecking',
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_check_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                value=value,
                retry_interval=retry_interval,
                timeout=timeout,
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def select(
            self,
            selector,
            element_index=0,
            value=None,
            index=None,
            label=None,
            retry_interval=None,
            timeout=None,
            window=0,
            animation=None,
    ):

        """
        Waits for at least one select element matching the given selector and
        selects an option specified by `value`, `index`, or `label`.

        If `animation` is set to true, an animation using the cursor is played.
        If animation is set to `None` the `Browser.animation` property is used
        to determine if an animation should be played.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        identifier = ''

        if value:
            identifier = f"value '{value}'"

        elif value:
            identifier = f"index '{index}'"

        elif label:
            identifier = f"label '{label}'"

        self.logger.info(
            "selecting option with %s in select with selector '%s' #%s in window %s with a timeout of %ss",  # NOQA
            identifier,
            selector,
            element_index,
            window,
            timeout,
        )

        return self._browser_evaluate(
            expression=commands.gen_window_select_command(
                window_index=window,
                selector=selector,
                element_index=element_index,
                value=value,
                index=index,
                label=label,
                retry_interval=retry_interval,
                timeout=timeout,
                animation=self._get_animations(animation),
            ),
        )

    # navigation ##############################################################
    @browser_function
    @frontend_function
    def navigate(self, url, window=0, animation=None):
        """
        Navigates the given window to the given URL.

        If `animation` is set to true, an animation is played that uses the
        cursor to click and fill the address bar of the window.

        If `animation` is set to `None` the `Browser.animation` property is
        used to determine if an animation should be played.
        """

        # TODO: add support for external sites besides 'localhost'
        # TODO: add support for cursor bootstrapping

        url = URL(url)

        # rewrite 'localhost' to '127.0.0.1' to prevent cookie settings loops
        # between the two origins (the frontend runs on '127.0.0.1')
        if url.host == 'localhost':
            url.host = '127.0.0.1'

        self.logger.info('navigating frontend to %s', url)

        return self._browser_evaluate(
            expression=commands.gen_window_navigate_command(
                window_index=window,
                url=str(url),
                animation=self._get_animations(animation),
            ),
        )

    def navigate_to_test_application(self, *args, **kwargs):
        """
        Navigates the given window to the Milan test application.
        """

        return self.navigate(
            url=self._frontend_server.get_test_application_url(),
            *args,
            **kwargs,
        )

    @browser_function
    def reload_frontend(self):
        """
        Reloads the Milan frontend.
        """

        self.logger.info('loading frontend')

        self._browser_navigate(url=self._frontend_server.get_frontend_url())

    @browser_function
    @frontend_function
    def highlight_elements(
        self,
        selectors,
        index=None,
        count=None,
        retry_interval=None,
        timeout=None,
        border_width=2,
        border_style='solid',
        border_color='#FF0000',
        padding=10,
        track=True,
        duration=None,
        window=0,
    ):

        """
        Waits for at least one element matching the given selector and
        selects and draws a marker around it.

        If `duration` is set to a number, the method will block for the given
        duration and the highlights will be removed afterwards.

        If `track` is set to true, the marker will track possible movements
        of the highlighted element.

        If `element_index` is set, a matching element with the given index
        is awaited and its attributes are used.

        If `retry_interval` is set to `None` the
        `Browser.selector_retry_interval` property is used instead.

        If `timeout` is set to `None` the
        `Browser.selector_timeout` property is used instead.
        """

        retry_interval = self._get_selector_retry_interval(retry_interval)
        timeout = self._get_selector_timeout(timeout)

        if not isinstance(selectors, (list, tuple)):
            selectors = [selectors]

        return self._browser_evaluate(
            expression=commands.gen_window_highlight_elements_command(
                window_index=window,
                selectors=selectors,
                index=index,
                count=count,
                retry_interval=retry_interval,
                timeout=timeout,
                border_width=border_width,
                border_style=border_style,
                border_color=border_color,
                padding=padding,
                track=track,
                duration=duration,
            ),
        )

    @browser_function
    @frontend_function
    def remove_highlights(self, window=0):
        """
        Removes all highlight markers in the given window.
        """

        return self._browser_evaluate(
            expression=commands.gen_window_remove_highlights_command(
                window_index=window,
            ),
        )

    # hooks ###################################################################
    @browser_function
    def _browser_navigate(self, url):
        raise NotImplementedError()

    @browser_function
    def _browser_evaluate(self, expression):
        raise NotImplementedError()

    @browser_function
    def _browser_set_size(self, width, height):
        raise NotImplementedError()

    def stop(self):
        """
        Stops the browser.

        When video capturing is still running, `Browser.stop_video_capturing`
        is called automatically.
        """

        raise NotImplementedError()

    def set_color_scheme(self, color_scheme):
        """
        Sets the color scheme of the browser.

        Possible values:
          - light
          - dark
        """

        raise NotImplementedError()

    @browser_function
    def screenshot(self, path):
        """
        Writes a screenshot of the current page to the given path.
        """

        raise NotImplementedError()

    @browser_function
    def start_video_capturing(
            self,
            path,
            delay=DEFAULT_VIDEO_CAPTURING_START_DELAY,
    ):

        """
        Starts video capturing into the given path.

        The video format is determined by the file extension of the given
        path.

        Possible video formats:
          - webm
          - mp4
          - gif
        """

        raise NotImplementedError()

    @browser_function
    def stop_video_capturing(
            self,
            delay=DEFAULT_VIDEO_CAPTURING_STOP_DELAY,
    ):

        raise NotImplementedError()
