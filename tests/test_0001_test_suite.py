import os


def test_artifacts_directory_fixture_first_round(milan_artifacts_directory):
    assert os.listdir(milan_artifacts_directory) == []

    path = os.path.join(milan_artifacts_directory, 'test.txt')

    with open(path, 'w+') as file_handle:
        file_handle.close()


def test_artifacts_directory_fixture_second_round(milan_artifacts_directory):
    assert os.listdir(milan_artifacts_directory) == ['test.txt']

    path = os.path.join(milan_artifacts_directory, 'test.txt')

    os.unlink(path)
