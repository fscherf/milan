#!/usr/bin/env python3

import threading
import traceback
import sys
import os

from milan.utils.json_rpc import JsonRpcMessage
from milan.executables import get_executable
from milan.utils.process import Process
from milan.utils.stream import Stream


def log(*args):
    message = ''

    for arg in args:
        message += str(arg)

    log_file.write(f'{message}\n')
    log_file.flush()


def log_cdp_message(issuer, message):
    issuer = issuer.ljust(12, ' ')
    message_length = str(len(message)).rjust(5, ' ')
    json_rpc_message = JsonRpcMessage(payload=message[:-1].decode())
    message_type = json_rpc_message.type.ljust(12, ' ')

    log(f'{issuer}  {message_type}  {message_length}  {message}')


def handle_debugging_pipe_in():
    try:
        while True:
            message = debugging_pipe_in.read_message()
            message += b'\0'

            log_cdp_message('playwright', message)
            browser_debugging_pipe_in.write(message)

    except Exception:
        for line in traceback.format_exc().splitlines():
            log(f'ERROR: {line}')


def handle_browser_debugging_pipe_out():
    try:
        while True:
            message = browser_debugging_pipe_out.read_message()
            message += b'\0'

            log_cdp_message('browser', message)
            debugging_pipe_out.write(message)

    except Exception:
        for line in traceback.format_exc().splitlines():
            log(f'ERROR: {line}')


if __name__ == '__main__':
    try:

        # find browser executable
        browser_name = os.path.basename(sys.argv[1])
        browser_executable = get_executable(browser_name)
        browser_command = [browser_executable, *sys.argv[2:]]

        # setup log
        log_file = open('playwright.log', 'w')

        log('=== Browser Command ===')
        log(browser_command[0])

        for part in browser_command[1:]:
            log(f'    {part}')

        log()

        log('=== CDP Traffic ===')

        # start browser
        proc = Process(
            command=browser_command,
            open_fds=(3, 4),

            # this is necessary for firefox
            # playwright seems to wait for some output on stdout or stderr on
            # firefox's startup
            capture_stdout=False,
        )

        browser_debugging_pipe_in = proc.get_writable_stream(3)
        browser_debugging_pipe_out = proc.get_readable_stream(4)

        # open debugging pipe
        debugging_pipe_in = Stream(3)
        debugging_pipe_out = Stream(4)

        # start debugging pipe handler threads
        threading.Thread(
            target=handle_debugging_pipe_in,
        ).start()

        threading.Thread(
            target=handle_browser_debugging_pipe_out,
        ).start()

    except Exception:
        for line in traceback.format_exc().splitlines():
            log(f'ERROR: {line}')
