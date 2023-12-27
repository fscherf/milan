import select
import os


class Stream:

    @classmethod
    def get_readable_stream(cls, path):
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)

        return cls(fd=fd)

    @classmethod
    def get_writable_stream(cls, path):
        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)

        return cls(fd=fd)

    def __init__(self, fd):
        self.fd = fd

        self._buffer = b''
        self._message_queue = []

    def __repr__(self):
        return f'<Stream({self.fd=})>'

    def close(self):
        return os.close(self.fd)

    def read(self, length):
        return os.read(self.fd, length)

    def write(self, data):
        return os.write(self.fd, data)

    def read_message(self, delimiter=b'\0', chunk_size=4096):

        # return the oldest pending message from the message queue
        # if not empty
        if self._message_queue:
            return self._message_queue.pop(0)

        while True:

            # wait for fd to become readable
            select.select([self.fd], [], [])

            # read chunks
            while True:
                chunk = self.read(chunk_size)
                self._buffer = self._buffer + chunk

                # there is at least one complete message in the buffer
                if delimiter in self._buffer:
                    break

                # we read less than our chunk size, without finding a message
                # we have to wait for select again
                if len(chunk) < chunk_size:
                    break

            # no complete message in buffer
            # waiting for select
            if delimiter not in self._buffer:
                continue

            # split buffer into messages
            for message in self._buffer.split(delimiter):
                if not message:
                    continue

                self._message_queue.append(message)

            # if the buffer does not end with the given delimiter, the last
            # message in `self.messages` is incomplete
            if not self._buffer.endswith(delimiter):
                self._buffer = self._message_queue.pop(-1)

            else:
                self._buffer = b''

            # return message from the message queue
            return self.read_message(
                delimiter=delimiter,
                chunk_size=chunk_size,
            )
