import shutil
import os

import pytest

ARTIFACTS_DIR = '/app/artifacts'


@pytest.fixture(scope='session')
def artifacts_dir():
    if not os.path.exists(ARTIFACTS_DIR):
        os.makedirs(ARTIFACTS_DIR)

    for rel_path in os.listdir(ARTIFACTS_DIR):
        abs_path = os.path.join(ARTIFACTS_DIR, rel_path)

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)

        else:
            os.unlink(abs_path)
