from milan.executables import get_executable
from milan.cdp_browser import CdpBrowser


class Firefox(CdpBrowser):
    def __init__(
            self,
            *args,
            executable=None,
            headless=True,
            **kwargs,
    ):

        self.executable = executable
        self.headless = headless

        if not self.executable:
            self.executable = get_executable('firefox')

        super().__init__(*args, **kwargs)

    def _get_browser_command(self, kwargs):
        return [
            self.executable,
            '--headless' if self.headless else '',
            f'--remote-debugging-port={self.debug_port}',
            '--remote-allow-origins=*',
            f'--profile={self.profile_id}',
            '--no-sandbox',
            'about:blank',
        ]

    def is_firefox(self):
        return True
