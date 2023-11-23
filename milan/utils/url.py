import urllib


class URL:
    @classmethod
    def normalize(cls, url_string):
        return str(cls(url_string))

    def __init__(self, url_string=''):
        url_string = str(url_string)

        if (not url_string.startswith('http') and
                not url_string.startswith('ws')):

            url_string = f'http://{url_string}'

        parse_result = urllib.parse.urlparse(url_string)

        self.protocol = parse_result.scheme
        self.host, self.port = (parse_result.netloc.split(':') + [''])[0:2]
        self.path = parse_result.path
        self.query = parse_result.query
        self.fragment = parse_result.fragment

    def __str__(self):
        url = f'{self.protocol}://{self.host}'

        if self.port:
            url = f'{url}:{self.port}'

        if self.path:
            path = self.path

            if path.startswith('/'):
                path = path[1:]

            url = f'{url}/{path}'

        if self.query:
            url = f'{url}?{self.query}'

        if self.fragment:
            url = f'{url}#{self.fragment}'

        return url

    def __repr__(self):
        return f'<URL({str(self)})>'

    @property
    def server(self):
        server = f'{self.protocol}://{self.host}'

        if self.port:
            server = f'{server}:{self.port}'

        return server
