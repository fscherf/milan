import shutil
import os

import urllib3
import pytest

from milan.utils.process import Process
from milan.utils.misc import retry

DEBUG = False

TEST_ARTIFACTS_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    'artifacts',
)


@pytest.fixture(scope='session')
def _setup_milan_artifacts_directory():
    if not os.path.exists(TEST_ARTIFACTS_DIRECTORY):
        os.makedirs(TEST_ARTIFACTS_DIRECTORY)

    for rel_path in os.listdir(TEST_ARTIFACTS_DIRECTORY):
        abs_path = os.path.join(TEST_ARTIFACTS_DIRECTORY, rel_path)

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)

        else:
            os.unlink(abs_path)


@pytest.fixture
def milan_artifacts_directory(_setup_milan_artifacts_directory):
    assert os.path.exists(TEST_ARTIFACTS_DIRECTORY)

    old_cwd = os.getcwd()

    os.chdir(TEST_ARTIFACTS_DIRECTORY)

    yield TEST_ARTIFACTS_DIRECTORY

    os.chdir(old_cwd)


@pytest.fixture
def start_web_app():
    processes = []

    def _start_web_app(command, await_port=None):
        process = Process(
            command=command,
            capture_stdout=False,
        )

        processes.append(process)

        if await_port:
            app_url = f'http://127.0.0.1:{await_port}'

            @retry
            def _await_app_port():
                urllib3.request(method='get', url=app_url)

            try:
                _await_app_port()

            except Exception:
                raise RuntimeError(f'{app_url} did not open')

        return process

    yield _start_web_app

    for process in processes:
        process.stop()


@pytest.fixture(autouse=True, scope='session')
def embed(request):
    def _run_rlpython():
        import rlpython
        rlpython.embed()

    if DEBUG:
        request.addfinalizer(_run_rlpython)
