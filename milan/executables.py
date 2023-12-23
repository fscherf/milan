import logging
import os

logger = logging.getLogger('milan.executables')

LOCAL_PLAYWRIGHT_ROOT = '~/.cache/ms-playwright'
GLOBAL_PLAYWRIGHT_ROOT = '/ms-playwright'
FFMPEG_OS_EXECUTABLE_PATH = '/usr/bin/ffmpeg'
FFPROBE_OS_EXECUTABLE_PATH = '/usr/bin/ffprobe'
CHROMIUM_OS_EXECUTABLE_PATH = '/usr/bin/chromium'
FIREFOX_OS_EXECUTABLE_PATH = '/usr/bin/firefox'

_executables_discovered = False

_executables = {
    'chromium': None,
    'firefox': None,
    'webkit': None,
    'ffmpeg': None,
    'ffprobe': None,
}


def _get_playwright_distribution_dir(playwright_root, prefix):
    for name in os.listdir(playwright_root):
        if name.startswith(prefix):
            return os.path.join(playwright_root, name)


def _discover_executables():
    global _executables_discovered

    logger.debug('discovering executables')

    # playwright ##############################################################
    playwright_root = ''

    logger.debug('searching for a playwright installation')

    if 'MILAN_IGNORE_PLAYWRIGHT' in os.environ:
        logger.debug('ignoring playwright')

    else:
        logger.debug('searching for a playwright installation')

        abs_local_playwright_root = os.path.expanduser(LOCAL_PLAYWRIGHT_ROOT)

        if os.path.exists(abs_local_playwright_root):
            logger.debug(
                'local playwright installation found: %s',
                abs_local_playwright_root,
            )

            playwright_root = abs_local_playwright_root

        elif os.path.exists(GLOBAL_PLAYWRIGHT_ROOT):
            logger.debug(
                'global playwright installation found: %s',
                GLOBAL_PLAYWRIGHT_ROOT,
            )

            playwright_root = GLOBAL_PLAYWRIGHT_ROOT

    # chromium ################################################################
    logger.debug('searching for chromium executable')

    # playwright
    if playwright_root:
        playwright_distribution_dir = _get_playwright_distribution_dir(
            playwright_root=playwright_root,
            prefix='chromium-',
        )

        path = os.path.join(playwright_distribution_dir, 'chrome-linux/chrome')

        if os.path.exists(path):
            logger.debug(
                'chromium executable in playwright installation found: %s',
                path,
            )

        _executables['chromium'] = path

    # os
    if not _executables['chromium']:
        if os.path.exists(CHROMIUM_OS_EXECUTABLE_PATH):
            logger.debug(
                'chromium executable in OS found: %s',
                CHROMIUM_OS_EXECUTABLE_PATH,
            )

            _executables['chromium'] = CHROMIUM_OS_EXECUTABLE_PATH

    # not found
    if not _executables['chromium']:
        logger.debug('no chromium executable found')

    # firefox #################################################################
    logger.debug('searching for firefox executable')

    # playwright
    if playwright_root:
        playwright_distribution_dir = _get_playwright_distribution_dir(
            playwright_root=playwright_root,
            prefix='firefox-',
        )

        path = os.path.join(playwright_distribution_dir, 'firefox/firefox')

        if os.path.exists(path):
            logger.debug(
                'firefox executable in playwright installation found: %s',
                path,
            )

        _executables['firefox'] = path

    # os
    if not _executables['firefox']:
        if os.path.exists(FIREFOX_OS_EXECUTABLE_PATH):
            logger.debug(
                'firefox executable in OS found: %s',
                FIREFOX_OS_EXECUTABLE_PATH,
            )

            _executables['firefox'] = FIREFOX_OS_EXECUTABLE_PATH

    # not found
    if not _executables['firefox']:
        logger.debug('no firefox executable found')

    # webkit ##################################################################
    logger.debug('searching for webkit executable')

    # playwright
    if playwright_root:
        playwright_distribution_dir = _get_playwright_distribution_dir(
            playwright_root=playwright_root,
            prefix='webkit-',
        )

        path = os.path.join(playwright_distribution_dir, 'pw_run.sh')

        if os.path.exists(path):
            logger.debug(
                'webkit executable in playwright installation found: %s',
                path,
            )

        _executables['webkit'] = path

    # not found
    if not _executables['webkit']:
        logger.debug('no webkit executable found')

    # ffmpeg ##################################################################
    logger.debug('searching for ffmpeg executable')

    # os
    if os.path.exists(FFMPEG_OS_EXECUTABLE_PATH):
        logger.debug(
            'ffmpeg executable found in OS: %s',
            FFMPEG_OS_EXECUTABLE_PATH,
        )

        _executables['ffmpeg'] = FFMPEG_OS_EXECUTABLE_PATH

    # not found
    if not _executables['ffmpeg']:
        logger.debug('no ffmpeg executable found')

    # ffprope #################################################################
    logger.debug('searching for ffprobe executable')

    # os
    if os.path.exists(FFPROBE_OS_EXECUTABLE_PATH):
        logger.debug(
            'ffprobe executable found in OS: %s',
            FFPROBE_OS_EXECUTABLE_PATH,
        )

        _executables['ffprobe'] = FFPROBE_OS_EXECUTABLE_PATH

    # not found
    if not _executables['ffprobe']:
        logger.debug('no ffprobe executable found')

    # finish ##################################################################
    _executables_discovered = True

    logger.debug('executable discovery done')


def get_executable(name):
    if not _executables_discovered:
        _discover_executables()

    if name not in _executables:
        raise FileNotFoundError(f'no {name} executable found')

    return _executables[name]
