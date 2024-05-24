import pytest


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_resizing(browser_name):
    from milan import get_browser_by_name

    browser_class = get_browser_by_name(browser_name)

    with browser_class.start() as browser:
        # the window size should be smaller than the browser size
        # because of the gap around the window

        # browser resize
        browser.set_size(1280, 720, even_values=False)

        current_browser_size = browser.get_size()
        current_window_size = browser.get_window_size()

        assert current_browser_size['width'] == 1280
        assert current_browser_size['height'] == 720
        assert current_window_size['width'] < 1280
        assert current_window_size['height'] < 720

        # window resize
        browser.set_window_size(1280, 720, even_values=False)

        current_browser_size = browser.get_size()
        current_window_size = browser.get_window_size()

        assert current_browser_size['width'] > 1280
        assert current_browser_size['height'] > 720
        assert current_window_size['width'] == 1280
        assert current_window_size['height'] == 720

        # even values
        browser.set_size(1023, 799, even_values=True)

        current_browser_size = browser.get_size()

        assert current_browser_size['width'] == 1024
        assert current_browser_size['height'] == 800
