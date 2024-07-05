import pytest


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_evaluate(browser_name):
    from milan import get_browser_by_name

    browser_class = get_browser_by_name(browser_name)

    with browser_class.start(animations=False) as browser:
        browser.split()

        # window evaluate
        assert browser.evaluate('1 + 1') == 2
        assert browser.evaluate('1 + 1', window=0) == 2
        assert browser.evaluate('1 + 1', window=1) == 2

        # test quoting
        assert browser.evaluate("'1' + '1'") == '11'
        assert browser.evaluate('"1" + "1"') == '11'
        assert browser.evaluate('\'1\' + "1"') == '11'
        assert browser.evaluate("'1' + \"1\"") == '11'

        # browser evaluate
        assert browser.evaluate('window["milan"] !== undefined', window=None)
        assert not browser.evaluate('window["milan"] !== undefined')
        assert not browser.evaluate('window["milan"] !== undefined', window=0)

        # test state
        assert not browser.evaluate('window.foo')
        assert not browser.evaluate('window.foo', window=0)

        browser.evaluate('window.foo="foo"')

        assert browser.evaluate('window.foo') == 'foo'
        assert browser.evaluate('window.foo', window=0) == 'foo'
        assert not browser.evaluate('window.foo', window=1)
