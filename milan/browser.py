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
    @browser_function
    @frontend_function
    def evaluate(self, expression, window=0):

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
        return self._browser_evaluate(
            expression=commands.gen_window_manager_get_size_command(),
        )

    @browser_function
    def set_size(self, width=0, height=0, even_values=True):
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
        return self._browser_evaluate(
            expression=commands.gen_window_manager_get_window_count_command(),
        )

    @frontend_function
    @browser_function
    def split(self):
        self.logger.info('splitting window')

        return self._browser_evaluate(
            expression=commands.gen_window_manager_split_command(),
        )

    @frontend_function
    @browser_function
    def set_background_url(self, url):
        return self._browser_evaluate(
            expression=commands.gen_window_manager_set_background_url_command(
                url=url,
            ),
        )

    @frontend_function
    @browser_function
    def set_watermark(self, text):
        return self._browser_evaluate(
            expression=commands.gen_window_manager_set_watermark_command(
                text=text,
            ),
        )

    @frontend_function
    @browser_function
    def set_background(self, background):
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
        self.logger.info('showing cursor')

        return self._browser_evaluate(
            expression=commands.gen_cursor_show_command(),
        )

    @frontend_function
    @browser_function
    def hide_cursor(self):
        self.logger.info('hiding cursor')

        return self._browser_evaluate(
            expression=commands.gen_cursor_hide_command(),
        )

    @frontend_function
    @browser_function
    def cursor_is_visible(self):
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
        self.logger.info('moving cursor to home')

        return self._browser_evaluate(
            expression=commands.gen_cursor_move_to_home_command(
                animation=self._get_animations(animation),
            ),
        )

    @frontend_function
    @browser_function
    def get_cursor_position(self):
        return self._browser_evaluate(
            expression=commands.gen_cursor_get_position_command(),
        )

    # window
    @frontend_function
    @browser_function
    def reload(self, window=0, animation=None):
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
        return self._browser_evaluate(
            expression=commands.gen_window_get_fullscreen_command(
                window_index=window,
            ),
        )

    @frontend_function
    @browser_function
    def set_fullscreen(self, window=0, fullscreen=True, decorations=True):
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
        raw_url = self._get_url(window=window)

        return URL(raw_url)

    # window
    @frontend_function
    @browser_function
    def get_window_size(self, window=0):
        return self._browser_evaluate(
            expression=commands.gen_window_get_size_command(
                window_index=window,
            ),
        )

    def set_window_size(self, width, height, window=0, even_values=True):
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
        return self.navigate(
            url=self._frontend_server.get_test_application_url(),
            *args,
            **kwargs,
        )

    @browser_function
    def reload_frontend(self):
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
        raise NotImplementedError()

    def set_color_scheme(self, color_scheme):
        raise NotImplementedError()

    @browser_function
    def screenshot(self, path):
        raise NotImplementedError()

    @browser_function
    def start_video_capturing(
            self,
            path,
            delay=DEFAULT_VIDEO_CAPTURING_START_DELAY,
    ):

        raise NotImplementedError()

    @browser_function
    def stop_video_capturing(
            self,
            delay=DEFAULT_VIDEO_CAPTURING_STOP_DELAY,
    ):

        raise NotImplementedError()
