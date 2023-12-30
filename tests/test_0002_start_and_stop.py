import pytest


# sync API ####################################################################
@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_sync_start(browser_name):
    from milan import Chromium, Firefox, Webkit, BrowserStoppedError

    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[browser_name]

    browser = browser_class()

    assert browser.get_window_count() == 1

    browser.stop()

    with pytest.raises(BrowserStoppedError):
        browser.get_window_count()


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_sync_start_context_manager(browser_name):
    from milan import Chromium, Firefox, Webkit, BrowserStoppedError

    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[browser_name]

    _browser = None

    with browser_class.start() as browser:
        _browser = browser

        assert browser.get_window_count() == 1

    with pytest.raises(BrowserStoppedError):
        _browser.get_window_count()


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox'])
def test_sync_unexpected_stop(browser_name):
    # TODO: we don't test webkit here because playwright webkit can't be
    # terminated easily

    from milan import Chromium, Firefox, Webkit, BrowserStoppedError

    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[browser_name]

    with browser_class.start() as browser:
        assert browser.get_window_count() == 1

        browser.browser_process.terminate()
        browser.browser_process.wait()

        with pytest.raises(BrowserStoppedError):
            browser.get_window_count()


# async API ###################################################################
@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
@pytest.mark.asyncio
async def test_async_start_context_manager(browser_name):
    from milan import Chromium, Firefox, Webkit, BrowserStoppedError

    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[browser_name]

    _browser = None

    async with browser_class.start() as browser:
        _browser = browser

        assert await browser.get_window_count() == 1

    with pytest.raises(BrowserStoppedError):
        await _browser.get_window_count()


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox'])
@pytest.mark.asyncio
async def test_async_unexpected_stop(browser_name):
    # TODO: we don't test webkit here because playwright webkit can't be
    # terminated easily

    from milan import Chromium, Firefox, Webkit, BrowserStoppedError

    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[browser_name]

    async with browser_class.start() as browser:
        assert await browser.get_window_count() == 1

        browser.browser_process.terminate()
        browser.browser_process.wait()

        with pytest.raises(BrowserStoppedError):
            await browser.get_window_count()
