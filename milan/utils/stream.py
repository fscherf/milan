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

    def __repr__(self):
        return f'<Stream({self.fd=})>'

    def close(self):
        return os.close(self.fd)

    def read(self, length):
        chunk = b''

        # The os.read sometimes runs into an BlockingIOError or
        # in an resource not available error, even though we have set the fd
        # to non-blocking in get_readable_stream. I am not sure why, but
        # since we fall into a select call after read is done anyway, this is
        # not really a problem for now.
        try:
            chunk = os.read(self.fd, length)

        except BlockingIOError:
            pass

        except OSError as error:
            if error.errno == 11:  # Resource temporarily unavailable
                pass

            raise

        return chunk

    def write(self, data):
        return os.write(self.fd, data)

    def read_message(self, delimiter=b'\0', chunk_size=4096):
        while True:
            if delimiter in self._buffer:
                message, self._buffer = self._buffer.split(delimiter, 1)

                return message

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
