import logging
import urllib3
import time

from milan.cli.entry_points import shell
from milan.utils.process import Process
from milan import get_browser_by_name
from milan.utils.imports import load
from milan.utils.misc import retry

ENTRY_POINTS = {
    'shell': shell,
}

logger = logging.getLogger('milan')


def run(cli_args):
    app_process = None
    browser = None

    try:

        # load entry points
        # prepare
        entry_point_prepare = cli_args['prepare']

        if entry_point_prepare:
            logger.info(
                "loading prepare entry point '%s'",
                entry_point_prepare,
            )

            entry_point_prepare = load(entry_point_prepare)

        # main
        entry_point_main = ENTRY_POINTS.get(cli_args['entry-point'], '')

        logger.info("loading entry point '%s'", cli_args['entry-point'])

        if not entry_point_main:
            entry_point_main = load(cli_args['entry-point'])

        # start app
        if cli_args['run-app']:
            logger.info('starting app "%s"', cli_args['run-app'])

            app_process = Process(
                command=cli_args['run-app'],
                logger=logging.getLogger('app'),
            )

        # await app port
        if cli_args['await-app-port'] > 0:
            app_url = f"http://127.0.0.1:{cli_args['await-app-port']}"

            logger.info('waiting for %s to open', app_url)

            @retry
            def _await_app_port():
                urllib3.request(method='get', url=app_url)

            try:
                _await_app_port()

            except Exception:
                raise RuntimeError(f'{app_url} did not open')

        # start browser
        browser_args = {
            'executable': cli_args['executable'],
            'headless': cli_args['headless'],
            'user_data_dir': cli_args['user-data-dir'],
            'animations': not cli_args['disable-animations'],
            'background_dir': cli_args['background-dir'],
            'watermark': cli_args['watermark'],
        }

        browser_class = get_browser_by_name(cli_args['browser'])

        logger.info('starting %s', browser_class.__name__)

        browser = browser_class(**browser_args)

        # run prepare entry point
        if entry_point_prepare:
            logger.info('starting prepare entry point')

            # disable animations
            # The prepare entry point is not captured, so there is no point
            # in having the animations running.
            browser.animations = False

            entry_point_prepare(
                browser=browser,
                cli_args=cli_args,
            )

            logger.info('prepare entry point finished')

            # reset browser
            browser.animations = not cli_args['disable-animations']

        # color scheme
        if cli_args['color-scheme']:
            logger.info('setting color-scheme to %s', cli_args['color-scheme'])

            browser.set_color_scheme(
                color_scheme=cli_args['color-scheme'],
            )

        # hide cursor
        if cli_args['hide-cursor']:
            logger.info('hiding cursor')

            browser.hide_cursor()

        # resize browser
        if (not cli_args['disable-resizing'] and
                cli_args['width'] and cli_args['height']):

            logger.info(
                'resizing to %sx%s',
                cli_args['width'],
                cli_args['height'],
            )

            browser.set_size(
                width=cli_args['width'],
                height=cli_args['height'],
            )

        # open additional windows
        if cli_args['windows'] > 1:
            additional_windows = cli_args['windows'] - 1

            logger.info('opening %s additional windows', additional_windows)

            for _ in range(additional_windows):
                browser.split()

        # open urls
        if cli_args['url']:
            for index, url in enumerate(cli_args['url']):
                browser.navigate(
                    url=url,
                    window=index,
                    animation=False,
                )

        # move cursor to home
        if not cli_args['hide-cursor']:
            browser.move_cursor_to_home(animation=False)

        # start video capturing
        output_path = cli_args.get('capture', '')

        if output_path:
            logger.info('starting video capture to %s', output_path)

            browser.start_video_capturing(
                output_path=output_path,
                frame_dir=cli_args.get('save-frames', ''),
            )

            # start delay
            if not cli_args['disable-delays'] and cli_args['start-delay']:
                logger.info(
                    'inserting start delay (%ss)',
                    cli_args['start-delay'],
                )

                time.sleep(cli_args['start-delay'])

        # run main entry point
        logger.info('starting entry point')

        entry_point_main(
            browser=browser,
            cli_args=cli_args,
        )

        logger.info('entry point finished')

        # stop delay
        if (output_path and
                not cli_args['disable-delays'] and
                cli_args['stop-delay']):

            logger.info(
                'inserting stop delay (%ss)',
                cli_args['stop-delay'],
            )

            time.sleep(cli_args['stop-delay'])

        # stop video capturing
        if output_path:
            logger.info('stopping video capture')

            browser.stop_video_capturing()

        # hold browser window open
        if (not cli_args['headless'] and
                not cli_args['close-on-exit'] and
                not cli_args['entry-point'] == 'shell'):

            logger.info('press ENTER to close the browser')

            input()

    except Exception as exception:
        logger.error('%s', exception)

        return exception

    finally:

        # stop browser
        if browser:
            browser.stop()

        # stop app
        if app_process:
            logger.info('stopping app')

            app_process.stop()
            app_process.wait()
