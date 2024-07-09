import pytest
import time


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_highlighting(browser_name, milan_artifacts_directory):
    from milan import get_browser_by_name, FrontendError

    browser_class = get_browser_by_name(browser_name)
    video_path = f'videos/{browser_name}-highlighting.mp4'

    with browser_class.start() as browser:
        browser.set_size(1280, 720)

        # capture video of the test (chrome only)
        if browser_name == 'chromium':
            browser.start_video_capturing(output_path=video_path)

        # navigate to test application
        browser.navigate_to_test_application()
        browser.await_elements('h1', text='Milan Test Application')

        # attempt to highlight a non existing element
        with pytest.raises(FrontendError) as excinfo:
            browser.highlight_elements('.non-existing-class')

        assert 'No matching elements found' in str(excinfo.value)

        # simple highlight
        browser.highlight_elements(
            '.class-1',
            padding=0,  # the elements are really close together
        )

        time.sleep(1)

        # highlight a moving element
        browser.click('#animation-start')
        browser.highlight_elements('#moving-button')

        time.sleep(1)

        # highlight for a given duration
        browser.highlight_elements(
            '.class-2',
            padding=0,  # the elements are really close together
            border_color='blue',
            duration=2,
        )

        time.sleep(1)

        # finish
        if browser_name == 'chromium':
            browser.stop_video_capturing()

        browser.screenshot(f'screenshots/{browser_name}-highlighting.png')
