from argparse import ArgumentParser
import time

from simple_logging_setup import setup
import debugpy

from milan.utils.background_loop import BackgroundLoop
from milan import Chromium, Firefox, Webkit
from milan.utils.process import Process
from milan.utils.http import HttpClient
from milan.utils.misc import retry

BROWSER = 'chromium'
HEADLESS = False
DEBUGGER = False
DEBUGGER_PORT = 5678


def run_form_demo(browser, output_path=None, frame_dir=None):
    browser.resize(1280, 720)

    # start video capturing:
    if output_path:
        browser.start_video_capturing(
            output_path=output_path,
            frame_dir=frame_dir,
        )

    # navigate to view
    browser.navigate('localhost:8080')
    browser.await_element('h1')
    browser.await_text('h1', 'Milan Demo Application')

    # fill out form
    browser.fill('#text-input', 'foo')
    browser.select('#select', label='Option 17')
    browser.check('#check-box', True)

    # open popup
    browser.click('#open')
    browser.fill('#text-input-2', 'bar')
    browser.click('#close')

    # stop video capturing
    if output_path:
        browser.stop_video_capturing()


def run_multi_window_demo(browser, output_path=None, frame_dir=None):
    browser.resize(1280, 720)

    # start video capturing:
    if output_path:
        browser.start_video_capturing(
            output_path=output_path,
            frame_dir=frame_dir,
        )

    # open second window
    if browser.get_window_count() < 2:
        browser.split()

    # open first popup
    browser.navigate('localhost:8080', window=0)
    browser.click('#open', window=0)
    browser.fill('#text-input-2', 'foo', window=0)

    # open second popup
    browser.navigate('localhost:8080', window=1)
    browser.click('#open', window=1)
    browser.fill('#text-input-2', 'bar', window=1)

    # stop video capturing
    if output_path:
        time.sleep(2)
        browser.stop_video_capturing()


if __name__ == '__main__':

    # start debugger
    if DEBUGGER:
        debugpy.listen(('localhost', DEBUGGER_PORT))
        debugpy.wait_for_client()

    # parse arguments
    parser = ArgumentParser()

    parser.add_argument(
        '--browser',
        choices=['chromium', 'firefox', 'webkit'],
        default=BROWSER,
    )

    parser.add_argument('--headless', action='store_true', default=HEADLESS)

    parser.add_argument('--run-form-demo', action='store_true')
    parser.add_argument('--run-multi-window-demo', action='store_true')
    parser.add_argument('--output-path')
    parser.add_argument('--frame-dir')

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

    # start demo application
    background_loop = BackgroundLoop()
    http_client = HttpClient(loop=background_loop.loop)

    demo_application = Process([
        '/usr/bin/env',
        'python3',
        'scripts/demo-application.py',
        '--host=0.0.0.0',
        '--port=8080',
        # '--serve-milan-frontend',
    ])

    @retry
    def _await_demo_application_started():
        status_code, _ = http_client.get(
            url='http://127.0.0.1:8080',
        )

        if status_code != 200:
            raise RuntimeError()

    _await_demo_application_started()
    http_client.stop()
    background_loop.stop()

    # start browser
    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[args.browser]

    browser_args = {
        'headless': args.headless,
    }

    with browser_class.start(**browser_args) as browser:
        if args.run_form_demo:
            run_form_demo(
                browser=browser,
                output_path=args.output_path,
                frame_dir=args.frame_dir,
            )

        elif args.run_multi_window_demo:
            run_multi_window_demo(
                browser=browser,
                output_path=args.output_path,
                frame_dir=args.frame_dir,
            )

        else:
            import rlpython
            rlpython.embed()

    # stop demo application
    demo_application.stop()
