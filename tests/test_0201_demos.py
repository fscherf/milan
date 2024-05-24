import pytest

import os

BROWSER_SIZE = (1280, 720, )
DEMO_ROOT = os.path.join(os.path.dirname(os.path.join(__file__)), '../demos')


@pytest.mark.demo
def test_form_demo(milan_artifacts_directory, start_web_app):
    import sys

    from milan import Chromium

    start_web_app(
        command=[
            sys.executable,
            os.path.join(DEMO_ROOT, 'demo-app.py'),
            '--port=8080',
        ],
        await_port=8080,
    )

    with Chromium.start() as browser:
        browser.set_size(*BROWSER_SIZE)
        browser.move_cursor_to_home()

        # start video capturing
        browser.start_video_capturing('demos/form.gif')

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
        browser.stop_video_capturing()


@pytest.mark.demo
def test_multi_window_demo(milan_artifacts_directory, start_web_app):
    import sys

    from milan import Chromium

    start_web_app(
        command=[
            sys.executable,
            os.path.join(DEMO_ROOT, 'demo-app.py'),
            '--port=8080',
        ],
        await_port=8080,
    )

    with Chromium.start() as browser:
        browser.set_size(*BROWSER_SIZE)
        browser.split()
        browser.move_cursor_to_home()

        # start video capturing
        browser.start_video_capturing('demos/multi-window.gif')

        # open first popup
        browser.navigate('localhost:8080', window=0)
        browser.click('#open', window=0)
        browser.fill('#text-input-2', 'foo', window=0)

        # open second popup
        browser.navigate('localhost:8080', window=1)
        browser.click('#open', window=1)
        browser.fill('#text-input-2', 'bar', window=1)

        # stop video capturing
        browser.stop_video_capturing()


@pytest.mark.xfail
@pytest.mark.demo
def test_youtube_trending_movies(milan_artifacts_directory):
    # This test is reliant on YouTube which is an external site.
    # Hence it is marked as xfailing in pytest.

    from milan import Chromium

    with Chromium.start() as browser:
        browser.set_size(*BROWSER_SIZE)
        browser.move_cursor_to_home()

        browser.start_video_capturing('demos/youtube.gif')

        browser.navigate('youtube.com')
        browser.click('#guide-button')
        browser.click('[title=Trending]')
        browser.click('[tab-title=Movies]')

        browser.stop_video_capturing()
