from simple_logging_setup import setup

from milan import Chromium, Firefox


def handle_command_line():
    setup(
        preset='cli',
        level='debug',
        exclude=[
            'websockets.client',
            'urllib3.connectionpool',
        ],
    )

    with Firefox.start() as browser:
        import rlpython
        rlpython.embed()
