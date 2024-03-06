import rlpython


def shell(browser, cli_args):
    print("a reference to the running browser is stored in 'browser'")

    return rlpython.embed(
        globals={
            'browser': browser,
            'cli_args': cli_args,
        },
        prompt=f'{browser.__class__.__name__} >>> ',
    )
