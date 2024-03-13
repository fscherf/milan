def main(browser, cli_args):

    # open first popup
    browser.navigate('localhost:8080', window=0)
    browser.click('#open', window=0)
    browser.fill('#text-input-2', 'foo', window=0)

    # open second popup
    browser.navigate('localhost:8080', window=1)
    browser.click('#open', window=1)
    browser.fill('#text-input-2', 'bar', window=1)
