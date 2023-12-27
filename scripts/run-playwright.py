import tempfile

from playwright.sync_api import sync_playwright

BROWSER = 'chromium'
VIDEO_PATH = 'playwright-video'
HEADLESS = False
VIDEO_CAPTURE = False


if __name__ == '__main__':
    temp_dir = tempfile.TemporaryDirectory()

    with sync_playwright() as p:
        browser_class = getattr(p, BROWSER)
        browser = browser_class.launch()

        browser = browser_class.launch(
            executable_path=f'scripts/{BROWSER}',
            headless=HEADLESS,
        )

        browser_context = browser.new_context(
            record_video_dir=VIDEO_PATH,
            record_video_size={
                'width': 800,
                'height': 600,
            },
        )

        page = browser_context.new_page()

        import rlpython
        rlpython.embed()
