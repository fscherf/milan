def main(browser, cli_args):

    # navigate to view
    browser.navigate('localhost:8080')
    browser.await_element('h1')
    browser.await_text('h1', 'Milan Demo Application')

    # fill out form
    browser.fill('#text-input', 'foo')
    browser.select('#select', label='Option 17')
    browser.check('#check-box', True)

    # open popup
    browser.click('#open')
    browser.fill('#text-input-2', 'bar')
    browser.click('#close')
