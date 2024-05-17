import pytest


@pytest.mark.parametrize('browser_name', ['chromium', 'firefox', 'webkit'])
@pytest.mark.parametrize('window', [0, 1])
def test_dom_api(browser_name, window):
    from milan import get_browser_by_name, FrontendError

    browser_class = get_browser_by_name(browser_name)

    with browser_class.start(animations=False) as browser:
        if window > 0:
            browser.split()

        browser.navigate_to_test_application(window=window)

        # selectors: await elements
        # existing element
        browser.await_elements('#selectors .class-1', window=window)

        # non existing element
        assert browser.await_elements(
            '#selectors .not-existing-class',
            present=False,
            window=window,
        ) == []

        with pytest.raises(FrontendError) as excinfo:
            browser.await_elements(
                '#selectors .not-existing-class',
                window=window,
            )

        assert str(excinfo.value) == 'No matching elements found'

        # multiple elements
        assert browser.await_elements(
            [
                '#selectors .class-1',
                '#selectors .class-2',
            ],
            window=window,
        ) == [
            '#selectors .class-1',
            '#selectors .class-2',
        ]

        assert browser.await_elements(
            [
                '#selectors .class-2',
                '#selectors .class-1',
            ],
            window=window,
        ) == [
            '#selectors .class-2',
            '#selectors .class-1',
        ]

        assert browser.await_elements(
            [
                '#selectors .class-1',
                '#selectors .not-existing-class',
            ],
            match_all=False,
            window=window,
        ) == [
            '#selectors .class-1',
        ]

        # element text
        assert browser.await_elements(
            '#selectors .class-1',
            text='class-1',
            window=window,
        ) == [
            '#selectors .class-1',
        ]

        with pytest.raises(FrontendError) as excinfo:
            assert browser.await_elements(
                '#selectors .class-1',
                text='non existing text',
                window=window,
            ) == [
                '#selectors .class-1',
            ]

        assert str(excinfo.value) == 'No matching elements found'

        # element count
        assert browser.await_elements(
            '#selectors .class-1',
            count=2,
            window=window,
        ) == [
            '#selectors .class-1',
        ]

        with pytest.raises(FrontendError) as excinfo:
            assert browser.await_elements(
                '#selectors .class-1',
                count=3,
                window=window,
            ) == [
                '#selectors .class-1',
            ]

        assert str(excinfo.value) == 'No matching elements found'

        # selectors: await elements (legacy)
        # existing element
        browser.await_element('#selectors .class-1', window=window)

        # non existing element
        with pytest.raises(FrontendError) as excinfo:
            browser.await_element(
                '#selectors .not-existing-class',
                window=window,
            )

        assert 'No element with selector' in str(excinfo.value)

        # multiple elements
        assert browser.await_element(
            [
                '#selectors .class-1',
                '#selectors .class-2',
            ],
            window=window,
        ) == '#selectors .class-1'

        assert browser.await_element(
            [
                '#selectors .class-2',
                '#selectors .class-1',
            ],
            window=window,
        ) == '#selectors .class-2'

        assert browser.await_element(
            [
                '#selectors .class-1',
                '#selectors .not-existing-class',
            ],
            window=window,
        ) == '#selectors .class-1'

        # selectors: check if elements exist
        assert browser.element_exists(
            '#selectors .class-1',
            window=window,
        ) == '#selectors .class-1'

        assert browser.element_exists(
            "#selectors [data-foo='bar']",
            window=window,
        ) == "#selectors [data-foo='bar']"

        assert browser.element_exists(
            [
                '#selectors .class-1',
                '#selectors .class-2',
            ],
            window=window,
        ) == '#selectors .class-1'

        assert browser.element_exists(
            [
                '#selectors .not-existing-class',
                '#selectors .class-1',
            ],
            window=window,
        ) == '#selectors .class-1'

        assert not browser.element_exists(
            '.not-existing-class',
            window=window,
        )

        assert browser.get_text(
            "#selectors [data-foo='bar']",
            window=window,
        ) == 'data-foo=bar'

        # element counting
        assert browser.get_element_count(
            '#selectors .class-1',
            window=window,
        ) == 2

        assert browser.get_element_count(
            '#selectors .class-2',
            window=window,
        ) == 2

        assert browser.get_element_count(
            '#selectors .class-3',
            window=window,
        ) == 1

        assert browser.get_element_count(
            '#selectors .class-4',
            window=window,
        ) == 0

        # element indices
        assert browser.get_text(
            '#selectors .class-1',
            window=window,
        ) == 'class-1'

        assert browser.get_text(
            '#selectors .class-1',
            element_index=1,
            window=window,
        ) == 'class-1,class-2'

        # text manipulation
        browser.set_text(
            '#selectors #empty',
            'foo',
            window=window,
        )

        text = browser.get_text(
            '#selectors #empty',
            window=window,
        )

        assert text == 'foo'

        # HTML manipulation
        browser.set_html(
            '#selectors #empty',
            "<span id='new'>new</span>",
            window=window,
        )

        browser.await_element(
            '#selectors #empty #new',
            window=window,
        )

        assert "<span" in browser.get_html(
            '#selectors #empty',
            window=window,
        )

        assert browser.get_text(
            '#selectors #empty #new',
            window=window,
        ) == 'new'

        browser.set_html(
            '#selectors #empty #new',
            '',
            window=window,
        )

        assert browser.get_html(
            '#selectors #empty #new',
            window=window,
        ) == ''

        # HTML attribute manipulation
        # get
        browser.set_html(
            '#selectors #empty',
            "<span id='new' foo='foo' bar='bar'></span>",
            window=window,
        )

        assert browser.get_attribute(
            '#selectors #empty #new',
            'foo',
            window=window,
        ) == 'foo'

        assert browser.get_attribute(
            '#selectors #empty #new',
            'bar',
            window=window,
        ) == 'bar'

        assert browser.get_attribute(
            '#selectors #empty #new',
            'baz',
            window=window,
        ) is None

        assert browser.get_attributes(
            '#selectors #empty #new',
            window=window,
        ) == {
            'id': 'new',
            'foo': 'foo',
            'bar': 'bar',
        }

        # set
        browser.set_attribute(
            '#selectors #empty #new',
            'foo',
            'foo2',
            window=window,
        )

        browser.set_attribute(
            '#selectors #empty #new',
            'baz',
            'baz',
            window=window,
        )

        assert browser.get_attribute(
            '#selectors #empty #new',
            'foo',
            window=window,
        ) == 'foo2'

        assert browser.get_attribute(
            '#selectors #empty #new',
            'baz',
            window=window,
        ) == 'baz'

        browser.set_attributes(
            '#selectors #empty #new',
            {
                'foo': 'foo3',
                'bar': 'bar3',
                'baz': 'baz3',
            },
            window=window,
        )

        assert browser.get_attributes(
            '#selectors #empty #new',
            window=window,
        ) == {
            'id': 'new',
            'foo': 'foo3',
            'bar': 'bar3',
            'baz': 'baz3',
        }

        # remove
        browser.remove_attribute(
            '#selectors #empty #new',
            'foo',
            window=window,
        )

        assert browser.get_attributes(
            '#selectors #empty #new',
            window=window,
        ) == {
            'id': 'new',
            'bar': 'bar3',
            'baz': 'baz3',
        }

        browser.remove_attributes(
            '#selectors #empty #new',
            ['bar', 'baz'],
            window=window,
        )

        assert browser.get_attributes(
            '#selectors #empty #new',
            window=window,
        ) == {
            'id': 'new',
        }

        # HTML class list manipulation
        # get
        browser.set_attribute(
            '#selectors #empty',
            'class',
            'foo bar baz',
            window=window,
        )

        assert sorted(browser.get_class_list(
            '#selectors #empty',
            window=window,
        )) == sorted(['foo', 'bar', 'baz'])

        # set
        browser.set_class_list(
            '#selectors #empty',
            ['foo2', 'bar2', 'baz2'],
            window=window,
        )

        assert sorted(browser.get_class_list(
            '#selectors #empty',
            window=window,
        )) == sorted(['foo2', 'bar2', 'baz2'])

        # clear
        browser.clear_class_list(
            '#selectors #empty',
            window=window,
        )

        assert browser.get_class_list(
            '#selectors #empty',
            window=window,
        ) == []

        # add
        browser.class_list_add(
            '#selectors #empty',
            'foo',
            window=window,
        )

        browser.class_list_add(
            '#selectors #empty',
            'bar',
            window=window,
        )

        browser.class_list_add(
            '#selectors #empty',
            'baz',
            window=window,
        )

        assert sorted(browser.get_class_list(
            '#selectors #empty',
            window=window,
        )) == sorted(['foo', 'bar', 'baz'])

        # remove
        browser.class_list_remove(
            '#selectors #empty',
            'baz',
            window=window,
        )

        assert sorted(browser.get_class_list(
            '#selectors #empty',
            window=window,
        )) == sorted(['foo', 'bar'])
