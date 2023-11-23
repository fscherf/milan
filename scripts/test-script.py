from argparse import ArgumentParser

from simple_logging_setup import setup

from milan.utils.http import http_get_request
from milan.utils.process import Process
from milan import Chromium, Firefox
from milan.utils.misc import retry


def run_form_test(browser):

    # resize browser
    browser.resize(1280, 720)

    # start video capturing
    browser.start_video_capturing('video.gif')

    # navigate to view
    browser.navigate('localhost:8080')
    browser.await_element('h1')
    browser.await_text('h1', 'Milan Test Application')

    # fill out form
    browser.fill('#text-input', 'foo')
    browser.select('#select', label='Option 17')
    browser.check('#check-box', True)

    # open popup
    browser.click('#open')
    browser.fill('#text-input-2', 'bar')
    browser.click('#close')

    # stop video capturing
    browser.stop_video_capturing()


if __name__ == '__main__':

    # parse arguments
    parser = ArgumentParser()

    parser.add_argument(
        '--browser',
        choices=['chromium', 'firefox'],
        default='chromium',
    )

    parser.add_argument('--headless', action='store_true')

    args = parser.parse_args()

    # setup logging
    setup(
        preset='cli',
        level='debug',
        exclude=[
            'websockets.client',
            'urllib3.connectionpool',
        ],
    )

    # start app under test
    app_under_test = Process([
        '/usr/bin/env',
        'python3',
        'scripts/test-application.py',
        '--host=0.0.0.0',
        '--port=8080',
        # '--serve-milan-frontend',
    ])

    @retry
    def _await_app_unter_test_started():
        http_get_request(url='http://127.0.0.1:8080')

    _await_app_unter_test_started()

    # start browser
    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
    }[args.browser]

    browser_args = {
        'headless': args.headless,
        'reverse_proxy_port': 9223,
    }

    with browser_class.start(**browser_args) as browser:
        run_form_test(browser)

#        import rlpython
#        rlpython.embed()

    # stop app under test
    app_under_test.stop()
