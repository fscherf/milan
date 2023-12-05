from milan.executables import get_executable
from milan.cdp_browser import CdpBrowser


class Firefox(CdpBrowser):
    def __init__(
            self,
            *args,
            executable=None,
            headless=True,
            debug_port=0,
            **kwargs,
    ):

        if not executable:
            executable = get_executable('firefox')

        super().__init__(
            *args,
            executable=executable,
            headless=headless,
            debug_port=debug_port,
            **kwargs,
        )

    def _get_browser_command(self, kwargs):
        return [
            kwargs['executable'],
            '--headless' if kwargs['headless'] else '',
            f'--remote-debugging-port={self.debug_port}',
            '--remote-allow-origins=*',
            f'--profile={self.profile_id}',
            '--no-sandbox',
            'about:blank',
        ]

    def is_firefox(self):
        return True
