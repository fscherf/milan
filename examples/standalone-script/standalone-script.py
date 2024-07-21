#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-

from milan import Chromium


if __name__ == '__main__':
    with Chromium.start(headless=True) as browser:

        # configure browser
        browser.set_size(1280, 720)
        browser.set_color_scheme('light')
        browser.move_cursor_to_home()

        # start video capturing
        browser.start_video_capturing('youtube.mp4')

        # navigate to YouTube landing page
        browser.navigate('youtube.com')

        # open sidebar
        browser.click('#guide-button')

        # click on "Trending"
        browser.click('[title=Trending]')

        # click on "Movies"
        browser.click('[tab-title=Movies]')

        # stop video capturing
        browser.stop_video_capturing()
