import time
import os

import pytest


def run_test_application_test(browser):
    def await_element_id(element_id):
        browser.await_text(selector='#element-id', text=element_id)

    def await_element_value(element_value):
        browser.await_text(selector='#element-value', text=element_value)

    # enable animations
    browser.click('#animation-start')

    # text input
    browser.fill('#text-input', 'foo')

    await_element_id('text-input')
    await_element_value('foo')

    # select: by value
    browser.select('#select', value='option-2')

    await_element_id('select')
    await_element_value('option-2')

    # select: by index
    browser.select('#select', index=0)

    await_element_id('select')
    await_element_value('option-1')

    # select: by label
    browser.select('#select', label='Option 3')

    await_element_id('select')
    await_element_value('option-3')

    # checkbox
    browser.check('#checkbox')

    await_element_id('checkbox')
    await_element_value('true')

    # button
    browser.check('#button')

    await_element_id('button')
    await_element_value('-')

    # button: out of viewport
    browser.check('#out-of-viewport-button')


@pytest.mark.parametrize('video_format', ['mp4', 'webm', 'gif'])
@pytest.mark.parametrize('fps', ['0fps', '24fps', '30fps', '60fps'])
@pytest.mark.parametrize('video_dimensions', [
    '0x0',
    '800x0',
    '0x800',
    '800x800',
])
@pytest.mark.parametrize('browser_name', ['chromium'])
def test_video_capturing(
        browser_name,
        video_dimensions,
        fps,
        video_format,
        milan_artifacts_directory,
):

    from milan.utils.misc import compare_numbers
    from milan.utils.media import Video
    from milan import Chromium

    def await_element_id(browser, element_id):
        browser.await_text(selector='#element-id', text=element_id)

    def await_element_value(browser, element_value):
        browser.await_text(selector='#element-value', text=element_value)

    # not running in CI
    # only running basic tests
    if 'MILAN_CI_TEST' not in os.environ:
        if (fps not in ('0fps',) or
                video_dimensions not in ('0x0', '800x0')):

            pytest.skip()

    browser_class = {
        'chromium': Chromium,
    }[browser_name]

    fps = int(fps[:-3])
    width, height = (int(i) for i in video_dimensions.split('x'))
    video_path = f'videos/{browser_name}-{width}x{height}-{fps}fps.{video_format}'  # NOQA

    with browser_class.start() as browser:
        browser.navigate_to_test_application()
        browser.animation = True
        browser.set_size(1280, 720)

        browser.start_video_capturing(
            output_path=video_path,
            width=width,
            height=height,
            fps=fps,
        )

        run_test_application_test(browser)

        browser.stop_video_capturing()

    # run video checks
    video = Video(video_path)

    assert video.duration > 0
    assert video.size > 0
    assert video_format in video.format

    if video_format == 'mp4':
        assert video.codec == 'h264'

    elif video_format == 'webm':
        assert video.codec == 'vp9'

    elif video_format == 'gif':
        assert video.codec == 'gif'

    # fps
    # default values
    if fps == 0:
        expected_frame_rate = {
            'mp4': 60,
            'webm': 60,
            'gif': 24,
        }[video_format]

        assert compare_numbers(expected_frame_rate, video.fps)

    # configured values
    # for gifs, only the default value really works
    elif video_format in ('mp4', 'webm'):
        assert compare_numbers(fps, video.fps)

    # scaling
    if width:
        assert video.width == width

    if height:
        assert video.height == height

    if not width and not height:
        assert video.width == 1280
        assert video.height == 720


@pytest.mark.parametrize('video_format', ['mp4'])
@pytest.mark.parametrize('video_dimensions', [
    '801x0',
    '0x801',
    '801x801',
])
@pytest.mark.parametrize('browser_name', ['chromium'])
def test_invalid_video_dimensions(
        browser_name,
        video_dimensions,
        video_format,
        milan_artifacts_directory,
):

    from milan import Chromium

    # not running in CI
    # only running basic tests
    if 'MILAN_CI_TEST' not in os.environ:
        if video_dimensions not in ('801x0',):
            pytest.skip()

    browser_class = {
        'chromium': Chromium,
    }[browser_name]

    width, height = (int(i) for i in video_dimensions.split('x'))
    video_path = f'videos/{browser_name}-{width}x{height}.{video_format}'

    with browser_class.start() as browser:

        # FIXME: there seems to be a race condition in milan.frontend.server
        time.sleep(1)

        with pytest.raises(ValueError):
            browser.start_video_capturing(
                output_path=video_path,
                width=width,
                height=height,
            )

    assert not os.path.exists(video_path)
