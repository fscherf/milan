import os

FFMPEG_EXECUTABLE_PATH = '/usr/bin/ffmpeg'
FFPROBE_EXECUTABLE_PATH = '/usr/bin/ffprobe'
CHROMIUM_EXECUTABLE_PATH = '/usr/bin/chromium'
FIREFOX_EXECUTABLE_PATH = '/usr/bin/firefox'


def _get_playwright_root():

    # local installation
    # ~/.cache/ms-playwright
    path = os.path.expanduser('~/.cache/ms-playwright')

    if os.path.exists(path):
        return path

    # global installation (docker)
    # /ms-playwright
    path = '/ms-playwright'

    if os.path.exists(path):
        return path

    # playwright is not installed
    return ''


def _get_playwright_distribution_dir(prefix):
    playwright_root = _get_playwright_root()

    for name in os.listdir(playwright_root):
        if name.startswith(prefix):
            return os.path.join(playwright_root, name)

    raise FileNotFoundError(os.path.join(playwright_root, f'{prefix}*'))


def find_ffmpeg_executable():
    if not os.path.exists(FFMPEG_EXECUTABLE_PATH):
        raise FileNotFoundError('no ffmpeg executable found')

    return FFMPEG_EXECUTABLE_PATH


def find_ffprobe_executable():
    if not os.path.exists(FFPROBE_EXECUTABLE_PATH):
        raise FileNotFoundError('no ffprobe executable found')

    return FFPROBE_EXECUTABLE_PATH


def find_chromium_executable():
    def _not_found():
        raise FileNotFoundError('no chromium executable found')

    # OS
    if not _get_playwright_root():
        if not os.path.exists(CHROMIUM_EXECUTABLE_PATH):
            _not_found()

        return CHROMIUM_EXECUTABLE_PATH

    # playwright
    distribution_dir = _get_playwright_distribution_dir('chromium-')
    executable = os.path.join(distribution_dir, 'chrome-linux/chrome')

    if not os.path.exists(executable):
        _not_found()

    return executable


def find_firefox_executable():
    def _not_found():
        raise FileNotFoundError('no firefox executable found')

    # OS
    if not _get_playwright_root():
        if not os.path.exists(FIREFOX_EXECUTABLE_PATH):
            _not_found()

        return FIREFOX_EXECUTABLE_PATH

    # playwright
    distribution_dir = _get_playwright_distribution_dir('firefox-')
    executable = os.path.join(distribution_dir, 'firefox/firefox')

    if not os.path.exists(executable):
        _not_found()

    return executable
