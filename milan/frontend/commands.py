import json
import os

from milan.utils.url import URL

FRONTEND_ROOT = os.path.join(os.path.dirname(__file__), 'frontend')
CURSOR_SOURCE_PATH = os.path.join(FRONTEND_ROOT, 'cursor.js')


class FrontendError(Exception):
    pass


def _gen_frontend_run_command(func, args=None):
    args_string = json.dumps(args or {})

    return f"""
        (async () => {{
            const args = JSON.parse('{args_string}');

            const returnValue = await milan.run({{
                func: {func},
                args: args,
            }});

            return JSON.stringify(returnValue);
        }})();
    """


def _gen_cursor_function_name(name):
    return f'milan.cursor.{name}'


def _gen_window_manager_function_name(name):
    return f'milan.windowManager.{name}'


def _gen_window_function_name(window_index, name):
    return f'milan.windowManager.getWindow({{index: {window_index}}}).{name}'


def parse_frontend_return_value(return_value):
    if isinstance(return_value, dict) and 'result' in return_value:
        return_value = return_value['result']['value']

    return_value = json.loads(return_value)

    if return_value['exitCode'] > 0:
        raise FrontendError(return_value['errorMessage'])

    return return_value.get('returnValue', None)


def frontend_function(function):
    def decorator(*args, **kwargs):
        return parse_frontend_return_value(function(*args, **kwargs))

    return decorator


# misc ########################################################################
def gen_frontend_url(base_url):
    frontend_url = URL(base_url)

    frontend_url.path = '_milan/frontend/'
    frontend_url.query = ''
    frontend_url.fragment = ''

    return str(frontend_url)


def get_cursor_source():
    return open(CURSOR_SOURCE_PATH, 'r').read()


# commands ####################################################################
# cursor
def gen_cursor_show_command():
    return _gen_frontend_run_command(
        func=_gen_cursor_function_name(
            name='show',
        ),
    )


def gen_cursor_hide_command():
    return _gen_frontend_run_command(
        func=_gen_cursor_function_name(
            name='hide',
        ),
    )


def gen_cursor_is_visible_command():
    return _gen_frontend_run_command(
        func=_gen_cursor_function_name(
            name='isVisible',
        ),
    )


def gen_cursor_move_to_command(x, y, animation):
    return _gen_frontend_run_command(
        func=_gen_cursor_function_name(
            name='moveTo',
        ),
        args={
            'x': x,
            'y': y,
            'animation': animation,
        },
    )


def gen_cursor_move_to_home_command(animation):
    return _gen_frontend_run_command(
        func=_gen_cursor_function_name(
            name='moveToHome',
        ),
        args={
            'animation': animation,
        },
    )


def gen_cursor_get_position_command():
    return _gen_frontend_run_command(
        func=_gen_cursor_function_name(
            name='getPosition',
        ),
    )


# window manager
def gen_window_manager_split_command():
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='split'),
    )


def gen_window_manager_get_window_count_command():
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='getWindowCount'),
    )


# window
def gen_window_navigate_command(window_index, url, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='navigate',
        ),
        args={
            'url': url,
            'animation': animation,
        },
    )


def gen_window_navigate_back_command(window_index, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='navigateBack',
        ),
        args={
            'animation': animation,
        },
    )


def gen_window_navigate_forward_command(window_index, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='navigateForward',
        ),
        args={
            'animation': animation,
        },
    )


def gen_window_reload_command(window_index, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='reload',
        ),
        args={
            'animation': animation,
        },
    )


# window: selectors
def gen_window_await_element_command(window_index, selector):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='awaitElement',
        ),
        args={
            'elementOrSelector': selector,
        },
    )


def gen_window_await_text_command(window_index, selector, text):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='awaitText',
        ),
        args={
            'elementOrSelector': selector,
            'text': text,
        },
    )


# window: user input
def gen_window_click_command(window_index, selector, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='click',
        ),
        args={
            'elementOrSelector': selector,
            'animation': animation,
        },
    )


def gen_window_fill_command(window_index, selector, value, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='fill',
        ),
        args={
            'elementOrSelector': selector,
            'value': value,
            'animation': animation,
        },
    )


def gen_window_check_command(window_index, selector, value, animation):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='check',
        ),
        args={
            'elementOrSelector': selector,
            'value': value,
            'animation': animation,
        },
    )


def gen_window_select_command(
        window_index,
        selector,
        value,
        index,
        label,
        animation,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='select',
        ),
        args={
            'elementOrSelector': selector,
            'value': value,
            'index': index,
            'label': label,
            'animation': animation,
        },
    )
