import os

import pytest


@pytest.mark.parametrize('image_format', ['jpeg', 'png'])
@pytest.mark.parametrize('image_size', ['0x0', '800x0', '0x800', '800x800'])
@pytest.mark.parametrize('browser_name', ['chromium'])
def test_screenshots(
        browser_name,
        image_size,
        image_format,
        milan_artifacts_directory,
):

    from milan.utils.media import Image
    from milan import Chromium

    # not running in CI
    # only running basic tests
    if 'MILAN_CI_TEST' not in os.environ:
        if image_size not in ('0x0', '800x0'):
            pytest.skip()

    browser_class = {
        'chromium': Chromium,
    }[browser_name]

    width, height = (int(i) for i in image_size.split('x'))
    image_path = f'{browser_name}-{width}x{height}.{image_format}'

    with browser_class.start() as browser:
        browser.navigate_to_test_application()
        browser.animation = True
        browser.resize(1280, 720)

        browser.screenshot(
            output_path=image_path,
            width=width,
            height=height,
        )

    # run image checks
    image = Image(image_path)

    assert image.size > 0
    assert image_format in image.format

    if width:
        assert image.width == width

    if height:
        assert image.height == height

    if not width and not height:
        assert image.width == 1280
        assert image.height == 720
