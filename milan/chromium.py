import webbrowser

from milan.cdp.websocket_browser import CdpWebsocketBrowser
from milan.browser_extensions import CHROMIUM_EXTENSIONS
from milan.executables import get_executable


class Chromium(CdpWebsocketBrowser):
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
            self.executable = get_executable('chromium')

        super().__init__(*args, **kwargs)

    def _get_browser_command(self, kwargs):
        """
        https://peter.sh/experiments/chromium-command-line-switches/
        """

        return [
            self.executable,
            '--headless=new' if self.headless else '',
            f'--user-data-dir={self.user_data_dir}',

            # browser extensions
            f'--load-extension={CHROMIUM_EXTENSIONS.MILAN}',

            # disable security features
            '--no-sandbox',
            '--disable-web-security',
            '--disable-site-isolation-trials',

            # disable optimizations
            '--disable-gpu',

            # remote debugging
            f'--remote-debugging-port={self.debug_port}',

            # initial page
            'about:blank',
        ]

    def is_chrome(self):
        return True

    def get_inspector_url(self):
        return self.cdp_client.get_frontend_url()

    def open_inspector(self):
        webbrowser.open_new_tab(self.get_inspector_url())

    # hooks
    def set_color_scheme(self, color_scheme):
        return self.cdp_websocket_client.emulation_set_emulated_media(
            prefers_color_scheme=color_scheme,
        )
