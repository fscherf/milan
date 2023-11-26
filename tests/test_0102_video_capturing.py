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
@pytest.mark.parametrize('fps', ['30fps', '60fps'])
@pytest.mark.parametrize('browser_name', ['chromium'])
def test_video_capturing(
        browser_name,
        fps,
        video_format,
        milan_artifacts_directory,
):

    from milan.utils.media import Video
    from milan import Chromium

    def await_element_id(browser, element_id):
        browser.await_text(selector='#element-id', text=element_id)

    def await_element_value(browser, element_value):
        browser.await_text(selector='#element-value', text=element_value)

    browser_class = {
        'chromium': Chromium,
    }[browser_name]

    video_path = f'{browser_name}-{fps}fps.{video_format}'
    fps = int(fps[:-3])

    with browser_class.start() as browser:
        browser.navigate_to_test_application()
        browser.animation = True
        browser.resize(1280, 720)

        browser.start_video_capturing(output_path=video_path, fps=fps)

        run_test_application_test(browser)

        browser.stop_video_capturing()

    # run video checks
    video = Video(video_path)

    assert video.duration > 0
    assert video.size > 0
    assert video_format in video.format

    if video_format in ('mp4', 'webm'):
        assert video.fps == fps

    if video_format == 'mp4':
        assert video.codec == 'h264'

    elif video_format == 'webm':
        assert video.codec == 'vp9'

    elif video_format == 'gif':
        assert video.fps == 24  # 24 is the max fps for gifs
