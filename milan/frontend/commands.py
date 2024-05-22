import functools
import json
import os

from milan.utils.url import URL

FRONTEND_ROOT = os.path.join(os.path.dirname(__file__), 'frontend')
CURSOR_SOURCE_PATH = os.path.join(FRONTEND_ROOT, 'cursor.js')


class FrontendError(Exception):
    pass


def _gen_frontend_run_command(func, args=None):
    args_string = json.dumps(args or {})

    # fix quoting for JavaScript
    # json.dumps quotes double quotes with only one backslash (\") but
    # JavaScript needs two backslashes (\\")
    args_string = repr(args_string)[1:-1]

    return f"""
        (async () => {{
            const args = JSON.parse(`{args_string}`);

            const returnValue = await milan.run({{
                func: {func},
                args: args,
            }});

            return JSON.stringify(returnValue);
        }})()
    """


def wrap_expression_into_function_declaration(expression):
    return f"""
        async () => {{
            return ({expression});
        }}
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


def frontend_function(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return parse_frontend_return_value(func(*args, **kwargs))

    return wrapper


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
def gen_evaluate_command(expression):
    return _gen_frontend_run_command(
        func='milan.evaluate',
        args={
            'expression': expression,
        },
    )


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
def gen_window_manager_get_size_command():
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='getSize'),
    )


def gen_window_manager_split_command():
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='split'),
    )


def gen_window_manager_get_window_count_command():
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='getWindowCount'),
    )


def gen_window_manager_set_background_url_command(url):
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='setBackgroundUrl'),
        args={
            'url': url,
        },
    )


def gen_window_manager_set_watermark_command(text):
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='setWatermark'),
        args={
            'text': text,
        },
    )


def gen_window_manager_force_rerender_command():
    return _gen_frontend_run_command(
        func=_gen_window_manager_function_name(name='forceRerender'),
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


def gen_window_get_fullscreen_command(window_index):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getFullscreen',
        ),
    )


def gen_window_set_fullscreen_command(window_index, fullscreen):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='setFullscreen',
        ),
        args={
            'fullscreen': fullscreen,
        },
    )


def gen_window_get_url_command(window_index):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getUrl',
        ),
    )


def gen_window_evaluate_command(window_index, expression):
    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='evaluate',
        ),
        args={
            'expression': expression,
        },
    )


# window: selectors
def gen_window_get_element_count_command(
        window_index,
        selector,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getElementCount',
        ),
        args={
            'selector': selector,
        },
    )


def gen_window_element_exists_command(
        window_index,
        selector,
        element_index,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='elementExists',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_await_element_command(
        window_index,
        selector,
        element_index,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='awaitElement',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'returnElement': False,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_await_text_command(
        window_index,
        selector,
        element_index,
        text,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='awaitText',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'text': text,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_get_text_command(
        window_index,
        selector,
        element_index,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getText',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_get_html_command(
        window_index,
        selector,
        element_index,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getHtml',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_set_html_command(
        window_index,
        selector,
        element_index,
        html,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='setHtml',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'html': html,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_get_attribute_command(
        window_index,
        selector,
        element_index,
        name,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getAttribute',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'name': name,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_get_attributes_command(
        window_index,
        selector,
        element_index,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='getAttributes',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_set_attributes_command(
        window_index,
        selector,
        element_index,
        attributes,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='setAttributes',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'attributes': attributes,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_remove_attributes_command(
        window_index,
        selector,
        element_index,
        names,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='removeAttributes',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'names': names,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_class_list_add_command(
        window_index,
        selector,
        element_index,
        names,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='classListAdd',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'names': names,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_class_list_remove_command(
        window_index,
        selector,
        element_index,
        names,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='classListRemove',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'names': names,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


# window: user input
def gen_window_click_command(
        window_index,
        selector,
        element_index,
        animation,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='click',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'animation': animation,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_fill_command(
        window_index,
        selector,
        element_index,
        value,
        animation,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='fill',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'value': value,
            'animation': animation,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_check_command(
        window_index,
        selector,
        element_index,
        value,
        animation,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='check',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'value': value,
            'animation': animation,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )


def gen_window_select_command(
        window_index,
        selector,
        element_index,
        value,
        index,
        label,
        animation,
        timeout,
        timeout_max,
):

    return _gen_frontend_run_command(
        func=_gen_window_function_name(
            window_index=window_index,
            name='select',
        ),
        args={
            'elementOrSelector': selector,
            'elementIndex': element_index,
            'value': value,
            'index': index,
            'label': label,
            'animation': animation,
            'timeout': timeout * 1000,
            'timeoutMax': timeout_max * 1000,
        },
    )
