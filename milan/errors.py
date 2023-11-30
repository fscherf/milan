class MilanError(Exception):
    pass


class BrowserError(MilanError):
    pass


class BrowserStoppedError(BrowserError):
    pass
