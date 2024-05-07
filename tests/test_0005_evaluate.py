import pytest


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_dom_api(browser_name):
    from milan import get_browser_by_name, FrontendError

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
        assert browser.evaluate('milan', window=None)

        with pytest.raises(FrontendError) as excinfo:
            assert browser.evaluate('milan')

        assert 'ReferenceError' in str(excinfo.value)

        with pytest.raises(FrontendError) as excinfo:
            assert not browser.evaluate('milan', window=0)

        assert 'ReferenceError' in str(excinfo.value)

        # test state
        assert not browser.evaluate('window.foo')
        assert not browser.evaluate('window.foo', window=0)

        browser.evaluate('window.foo="foo"')

        assert browser.evaluate('window.foo') == 'foo'
        assert browser.evaluate('window.foo', window=0) == 'foo'
        assert not browser.evaluate('window.foo', window=1)
