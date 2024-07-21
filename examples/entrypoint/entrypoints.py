def open_trending_movies(browser, cli_args):

    # navigate to YouTube landing page
    browser.navigate('youtube.com')

    # open sidebar
    browser.click('#guide-button')

    # click on "Trending"
    browser.click('[title=Trending]')

    # click on "Movies"
    browser.click('[tab-title=Movies]')
