import pytest


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
def test_form_inputs(browser_name):
    from milan import Chromium, Firefox, Webkit

    def await_element_id(browser, element_id):
        browser.await_text(selector='#element-id', text=element_id)

    def await_element_value(browser, element_value):
        browser.await_text(selector='#element-value', text=element_value)

    browser_class = {
        'chromium': Chromium,
        'firefox': Firefox,
        'webkit': Webkit,
    }[browser_name]

    with browser_class.start() as browser:
        browser.navigate_to_test_application()
        browser.animations = False

        # text input
        browser.fill('#text-input', 'foo')

        await_element_id(browser, 'text-input')
        await_element_value(browser, 'foo')

        # select: by value
        browser.select('#select', value='option-2')

        await_element_id(browser, 'select')
        await_element_value(browser, 'option-2')

        # select: by index
        browser.select('#select', index=0)

        await_element_id(browser, 'select')
        await_element_value(browser, 'option-1')

        # select: by label
        browser.select('#select', label='Option 3')

        await_element_id(browser, 'select')
        await_element_value(browser, 'option-3')

        # checkbox
        browser.check('#checkbox')

        await_element_id(browser, 'checkbox')
        await_element_value(browser, 'true')

        # button
        browser.check('#button')

        await_element_id(browser, 'button')
        await_element_value(browser, '-')
