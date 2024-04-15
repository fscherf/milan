def open_trending_movies(browser, cli_args):
    browser.navigate('youtube.com')
    browser.click('#guide-button')
    browser.click('[title=Trending]')
    browser.click('[tab-title=Movies]')
