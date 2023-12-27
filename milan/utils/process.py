import subprocess
import threading
import tempfile
import logging
import shlex
import os

from milan.utils.misc import unique_id, retry
from milan.utils.stream import Stream

PASS_FDS_PATH = os.path.join(os.path.dirname(__file__), 'pass-fds.sh')


class Process:
    def __init__(
            self,
            command,
            name='',
            on_stdout_line=None,
            capture_stdout=True,
            on_stop=None,
            open_fds=(),
            logger=None,
    ):

        self.command = command
        self.name = name
        self.on_stdout_line = on_stdout_line
        self.capture_stdout = capture_stdout
        self.on_stop = on_stop
        self.logger = logger

        self.id = unique_id()
        self.fifo_root = None

        if not self.logger:
            self.logger = logging.getLogger(f'milan.process.{self.id}')

        # parse command
        if not isinstance(self.command, list):
            self.command = shlex.split(self.command)

        self.command = [i for i in self.command if i]

        # find name
        if not self.name:
            self.name = [i for i in self.command[0].split('/') if i][-1]

        # setup additional fds
        if open_fds:
            # subprocess.Popen's pass_fds does not support fd mapping, as it
            # passes the parent process's fd numbers to the child process
            # as-is. Mapping these fds to arbitrary numbers is not directly
            # possible. As a workaround, we use a temp dir, which holds fifos
            # as pipe rendezvous points, and a bash script to open the fifos
            # on the correct fds on the child process.

            self.fifo_root = tempfile.TemporaryDirectory()
            fd_args = []

            for fifo_name in open_fds:
                fifo_name = str(fifo_name)
                fifo_path = os.path.join(self.fifo_root.name, fifo_name)

                os.mkfifo(fifo_path)

                fd_args.extend([fifo_name, fifo_path])

            # update command to use the pass-fds.sh shim
            self.command = [
                PASS_FDS_PATH,
                *fd_args,
                '--',
                *self.command,
            ]

        # start process
        self.logger.debug(f"starting {' '.join(self.command)}")

        popen_kwargs = {
            'args': self.command,
        }

        if self.capture_stdout:
            popen_kwargs.update({
                'stdin': subprocess.PIPE,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
            })

        elif self.on_stdout_line:
            self.logger.warning('`on_stdout_line` has no effect if `capture_stdout` is disabled')

        self.proc = subprocess.Popen(**popen_kwargs)

        # start process handling thread
        threading.Thread(
            target=self._handle_process,
            name=f'{self.logger.name}.stdout',
        ).start()

    def _handle_process(self):
        if self.capture_stdout:
            for line_bytes in self.proc.stdout:
                line = line_bytes.decode().strip()

                if not line:
                    continue

                self.logger.debug(line)

                if not self.on_stdout_line:
                    continue

                try:
                    self.on_stdout_line(line)

                except Exception:
                    self.logger.exception(
                        'exception raised while running %s',
                        self.on_stdout_line,
                    )

        # read the process exit code to prevent zombie processes
        self.wait()

        # process stopped
        self.logger.debug('process stopped')

        # close fifos
        if self.fifo_root:
            self.fifo_root.cleanup()

        # run on_stop hook
        if not self.on_stop:
            return

        self.logger.debug('running on_stop hook')

        try:
            self.on_stop(self)

        except Exception:
            self.logger.exception(
                'exception raised while running %s',
                self.on_stop,
            )

    def get_readable_stream(self, fd):
        return Stream.get_readable_stream(
            path=os.path.join(self.fifo_root.name, str(fd)),
        )

    def get_writable_stream(self, fd):
        # To open the writable side of a FIFO in nonblocking mode, the readable
        # side has to be open first. We don't get notified when the readable
        # side was open, so we retry a few times.
        #
        # "A process can open a FIFO in nonblocking mode. In this case, opening
        # for read-only succeeds even if no one has opened on the write side
        # yet and opening for write-only fails with ENXIO (no such device or
        # address) unless the other end has already been opened."
        #
        # (man 7 fifo)

        @retry
        def _get_stream():
            return Stream.get_writable_stream(
                path=os.path.join(self.fifo_root.name, str(fd)),
            )

        return _get_stream()

    def stdin_write(self, data):
        self.logger.debug('writing %s bytes to stdin', len(data))

        return self.proc.stdin.write(data)

    def stdin_close(self):
        self.logger.debug('closing stdin')

        return self.proc.stdin.close()

    def terminate(self):
        self.logger.debug('terminating process')

        return self.proc.terminate()

    def kill(self):
        self.logger.debug('killing process')

        return self.proc.kill()

    def wait(self):
        self.logger.debug('waiting for process to finish')

        return self.proc.wait()

    def stop(self):
        return self.terminate()
