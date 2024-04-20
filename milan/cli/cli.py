import argparse

import simple_logging_setup

from milan.cli.background_init import background_init
from milan import VERSION_STRING
from milan.cli.run import run

COMMANDS = {
    'version': lambda cli_args: print(VERSION_STRING),
    'background-init': background_init,
    'run': run,
}


def add_common_args(parser):
    parser.add_argument(
        '-l',
        '--log-level',
        choices=['debug', 'info', 'warn', 'error', 'critical'],
        default='info',
    )

    parser.add_argument(
        '--loggers',
        type=str,
        nargs='+',
    )

    parser.add_argument(
        '--traceback',
        action='store_true',
    )


def parse_command_line_args(argv):
    parser = argparse.ArgumentParser(prog='milan')

    sub_parser = parser.add_subparsers(
        dest='command',
        required=True,
    )

    # version #################################################################
    version_parser = sub_parser.add_parser('version')

    add_common_args(version_parser)

    # background-init #########################################################
    background_init_parser = sub_parser.add_parser('background-init')

    add_common_args(background_init_parser)

    background_init_parser.add_argument(
        'directory',
        nargs='?',
    )

    background_init_parser.add_argument(
        '--dry-run',
        action='store_true',
    )

    # run #####################################################################
    run_parser = sub_parser.add_parser('run')

    add_common_args(run_parser)

    # entry points
    run_parser.add_argument(
        'entry-point',
    )

    run_parser.add_argument(
        '--prepare',
        default='',
    )

    # browser args
    run_parser.add_argument(
        '--browser',
        default='chromium',
    )

    run_parser.add_argument(
        '--executable',
        default='',
    )

    run_parser.add_argument(
        '--user-data-dir',
        default='',
    )

    run_parser.add_argument(
        '--background-dir',
        default='',
    )

    run_parser.add_argument(
        '--watermark',
        default='',
    )

    run_parser.add_argument(
        '--color-scheme',
        default='',
    )

    run_parser.add_argument(
        '--headless',
        action='store_true',
    )

    run_parser.add_argument(
        '--hide-cursor',
        action='store_true',
    )

    run_parser.add_argument(
        '--disable-animations',
        action='store_true',
    )

    run_parser.add_argument(
        '--windows',
        type=int,
        default=1,
    )

    run_parser.add_argument(
        '--url',
        nargs='+',
    )

    # resizing
    run_parser.add_argument(
        '--disable-resizing',
        action='store_true',
    )

    run_parser.add_argument(
        '--width',
        type=int,
        default=1280,
    )

    run_parser.add_argument(
        '--height',
        type=int,
        default=720,
    )

    # capturing
    run_parser.add_argument(
        '--capture',
        default='',
    )

    run_parser.add_argument(
        '--save-frames',
        default='',
    )

    # delays
    run_parser.add_argument(
        '--disable-delays',
        action='store_true',
    )

    run_parser.add_argument(
        '--start-delay',
        type=float,
        default=1,
    )

    run_parser.add_argument(
        '--stop-delay',
        type=float,
        default=2,
    )

    # entry point options
    run_parser.add_argument(
        '--close-on-exit',
        action='store_true',
    )

    # app options
    run_parser.add_argument(
        '--run-app',
        default='',
    )

    run_parser.add_argument(
        '--await-app-port',
        type=int,
        default=0,
    )

    # parse args ##############################################################
    namespace = parser.parse_args(args=argv[1:])
    args = {}

    for key, value in vars(namespace).items():
        key = key.replace('_', '-')
        args[key] = value

    return args


def cli(argv, setup_logging=False):
    args = parse_command_line_args(argv=argv)
    exception = None

    # setup logging
    if setup_logging:
        simple_logging_setup.setup(
            preset='cli',
            level=args['log-level'],
            loggers=[

                # `run --await-app-port` uses urllib3 to check whether the apps
                # port opened. The retries are pretty noisy and the output is
                # not very useful.
                '-urllib3.connectionpool',

                *(args['loggers'] or []),
            ],
        )

    # run command
    command = COMMANDS[args['command']]
    exception = command(cli_args=args)

    if not exception:
        return 0

    if args['traceback']:
        raise exception

    return 1
