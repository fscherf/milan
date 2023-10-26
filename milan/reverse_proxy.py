import os

from milan.process import Process


class ReverseProxy:
    EXECUTABLE = '/usr/bin/socat'

    def __init__(self, port, remote_host, remote_port, logger=None):
        self.port = port
        self.remote_host = remote_host
        self.remote_port = remote_port

        if not os.path.join(self.EXECUTABLE):
            raise FileNotFoundError('socat is not installed')

        self.process = Process(
            command=[
                self.EXECUTABLE,
                f'tcp-listen:{self.port},reuseaddr,fork',
                f'tcp:{self.remote_host}:{self.remote_port}',
            ],
            logger=logger,
        )

    def stop(self):
        self.process.kill()
