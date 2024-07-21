import pytest


@pytest.mark.parametrize('resolution', ['1920x1080', '1280x720'])
@pytest.mark.parametrize('color_scheme', ['light', 'dark'])
@pytest.mark.parametrize('browser_name', ['chromium'])
def test_open_trending_movies(browser_name, color_scheme, resolution, artifacts_dir):
    from milan import get_browser_by_name

    browser_width, browser_height = [int(i) for i in resolution.split('x')]
    browser_class = get_browser_by_name(browser_name)

    browser_kwargs = {
        'headless': True,
    }

    with browser_class.start(**browser_kwargs) as browser:

        # configure browser
        browser.set_size(browser_width, browser_height)
        browser.set_color_scheme(color_scheme)
        browser.move_cursor_to_home()

        # start video capturing
        browser.start_video_capturing(
            f'/app/artifacts/{browser_name}-{color_scheme}-{resolution}.mp4',
        )

        # navigate to YouTube landing page
        # By default, YouTube should use the default device theme, but
        # for some reason sometime it doesn't.
        browser.navigate(f'youtube.com?theme={color_scheme}')

        # open sidebar
        browser.click('#guide-button')

        # click on "Trending"
        browser.click('[title=Trending]')

        # click on "Movies"
        browser.click('[tab-title=Movies]')

        # stop video capturing
        browser.stop_video_capturing()
