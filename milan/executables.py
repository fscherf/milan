import os

PLAYWRIGHT_ROOT = '/ms-playwright'
FFMPEG_EXECUTABLE_PATH = '/usr/bin/ffmpeg'
CHROMIUM_EXECUTABLE_PATH = '/usr/bin/chromium'
FIREFOX_EXECUTABLE_PATH = '/usr/bin/firefox'


def _running_in_playwright_docker_image():
    return os.path.isdir(PLAYWRIGHT_ROOT)


def _get_playwright_distribution_dir(prefix):
    for name in os.listdir(PLAYWRIGHT_ROOT):
        if name.startswith(prefix):
            return os.path.join(PLAYWRIGHT_ROOT, name)

    raise FileNotFoundError(os.path.join(PLAYWRIGHT_ROOT, f'{prefix}*'))


def find_ffmpeg_executable():
    if not os.path.exists(FFMPEG_EXECUTABLE_PATH):
        raise FileNotFoundError('no ffmpeg executable found')

    return FFMPEG_EXECUTABLE_PATH


def find_chromium_executable():
    def _not_found():
        raise FileNotFoundError('no chromium executable found')

    # OS
    if not _running_in_playwright_docker_image():
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
    if not _running_in_playwright_docker_image():
        if not os.path.exists(FIREFOX_EXECUTABLE_PATH):
            _not_found()

        return FIREFOX_EXECUTABLE_PATH

    # playwright
    distribution_dir = _get_playwright_distribution_dir('firefox-')
    executable = os.path.join(distribution_dir, 'firefox/firefox')

    if not os.path.exists(executable):
        _not_found()

    return executable
