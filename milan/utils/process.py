import subprocess
import threading
import logging
import shlex

from milan.utils.misc import unique_id


class Process:
    def __init__(
            self,
            command,
            name='',
            on_stdout_line=None,
            on_stop=None,
            logger=None,
    ):

        self.command = command
        self.name = name
        self.on_stdout_line = on_stdout_line
        self.on_stop = on_stop
        self.logger = logger

        self.id = unique_id()

        if not self.logger:
            self.logger = logging.getLogger(f'milan.process.{self.id}')

        # parse command
        if not isinstance(self.command, list):
            self.command = shlex.split(self.command)

        self.command = [i for i in self.command if i]

        # find name
        if not self.name:
            self.name = [i for i in self.command[0].split('/') if i][-1]

        # start process
        self.logger.debug(f"starting {' '.join(self.command)}")

        self.proc = subprocess.Popen(
            args=self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # start stdout/stderr reader thread
        threading.Thread(
            target=self._read_stdout,
            name=f'{self.logger.name}.stdout',
            args=[self.proc.stdout],
        ).start()

    def _read_stdout(self, pipe):
        for line_bytes in pipe:
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

        # process stopped
        self.logger.debug('process stopped')

        # read the process exit code to prevent zombie processes
        self.wait()

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
