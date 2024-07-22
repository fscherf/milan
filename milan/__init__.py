import logging

from milan.frontend.commands import FrontendError  # NOQA
from milan.chromium import Chromium  # NOQA
from milan.firefox import Firefox  # NOQA
from milan.webkit import Webkit  # NOQA
from milan.errors import *  # NOQA

VERSION = (0, 1, 4)
VERSION_STRING = '.'.join(str(i) for i in VERSION)

BROWSER = {
    'chromium': Chromium,
    'chrome': Chromium,
    'firefox': Firefox,
    'webkit': Webkit,
    'safari': Webkit,
}

logger = logging.getLogger('milan')


def get_browser_by_name(name):
    logging.debug('searching for a browser by name "%s"', name)

    _name = name.strip().lower()

    if _name not in BROWSER:
        raise RuntimeError(f'No browser with name "{name}" found')

    browser = BROWSER[_name]

    logging.debug('%s found', browser)

    return browser
