import time


def open_trending_movies(browser, cli_args):
    browser.navigate('youtube.com')
    browser.click('#guide-button')
    browser.click('[title=Trending]')

    time.sleep(1)  # give the page time to render
    browser.click('[tab-title=Movies]')
