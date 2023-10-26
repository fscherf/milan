import webbrowser

from milan.executables import find_chromium_executable
from milan.cdp_browser import CdpBrowser


class Chromium(CdpBrowser):
    def __init__(
            self,
            *args,
            executable=None,
            headless=True,
            debug_port=0,
            disable_web_security=False,
            **kwargs,
    ):

        if not executable:
            executable = find_chromium_executable()

        super().__init__(
            *args,
            executable=executable,
            headless=headless,
            debug_port=debug_port,
            disable_web_security=disable_web_security,
            **kwargs,
        )

    def _get_browser_command(self, kwargs):
        """
        https://peter.sh/experiments/chromium-command-line-switches/
        """

        return [
            kwargs['executable'],
            '--headless' if kwargs['headless'] else '',
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
