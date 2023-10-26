from argparse import ArgumentParser

from lona_picocss import install_picocss
from lona import App, View

from lona_picocss.html import (
    InlineButton,
    TextInput,
    CheckBox,
    Select2,
    Option2,
    Label,
    Modal,
    HTML,
    H1,
    H3,
)

from milan.lona import FrontendView


class FormTestView(View):
    def open_modal(self, input_event=None):
        with self.html.lock:
            self.modal.get_body().nodes = [
                H3('Modal'),

                Label(
                    'Text Input 2',
                    TextInput(_id='text-input-2'),
                ),
            ]

            self.modal.get_footer().nodes = [
                InlineButton(
                    'Close',
                    _id='close',
                    handle_click=self.close_modal,
                ),
            ]

            self.modal.open()

    def close_modal(self, input_event=None):
        self.modal.close()

    def handle_request(self, request):
        self.modal = Modal()

        self.html = HTML(
            H1('Milan Test Application'),

            Label(
                'Text Input',
                TextInput(_id='text-input'),
            ),
            Label(
                'Select',
                Select2(
                    *(Option2(f'Option {i}', value=f'option-{i}')
                      for i in range(50)),
                    _id='select',
                ),
            ),
            Label(
                CheckBox(_id='check-box'),
                'CheckBox',
            ),

            InlineButton(
                'Open Popup',
                _id='open',
                style='margin-top: 120vh',
                handle_click=self.open_modal,
            ),

            self.modal,
        )

        return self.html


if __name__ == '__main__':

    # parse command line args
    parser = ArgumentParser()

    parser.add_argument(
        '--serve-milan-frontend',
        action='store_true',
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8080,
    )

    args = parser.parse_args()

    # setup lona app
    app = App(__file__)

    app.settings.PICOCSS_THEME = 'dark'

    install_picocss(app, debug=True)

    app.route('/')(FormTestView)

    if args.serve_milan_frontend:
        app.route(
            '/_milan/frontend/<path:.*>',
            interactive=False,
        )(FrontendView)

    # run lona app
    app.run(
        host=args.host,
        port=args.port,
        parse_command_line=False,
    )
