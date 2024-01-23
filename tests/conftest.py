import shutil
import os

import pytest

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


@pytest.fixture(autouse=True, scope='session')
def embed(request):
    def _run_rlpython():
        import rlpython
        rlpython.embed()

    if DEBUG:
        request.addfinalizer(_run_rlpython)
