import webbrowser

from milan.executables import get_executable
from milan.cdp_browser import CdpBrowser


class Chromium(CdpBrowser):
    def __init__(
            self,
            *args,
            executable=None,
            headless=True,
            disable_web_security=False,
            **kwargs,
    ):

        self.executable = executable
        self.headless = headless
        self.disable_web_security = disable_web_security

        if not self.executable:
            self.executable = get_executable('chromium')

        super().__init__(*args, **kwargs)

    def _get_browser_command(self, kwargs):
        """
        https://peter.sh/experiments/chromium-command-line-switches/
        """

        return [
            self.executable,
            '--headless' if self.headless else '',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-web-security',
            f'--user-data-dir={self.user_data_dir.name}',
            f'--remote-debugging-port={self.debug_port}',
            '--remote-allow-origins=*',
            'about:blank',
        ]

    def is_chrome(self):
        return True

    def get_inspector_url(self):
        return self.cdp_client.get_frontend_url()

    def open_inspector(self):
        webbrowser.open_new_tab(self.get_inspector_url())
