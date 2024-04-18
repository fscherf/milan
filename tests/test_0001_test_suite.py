import os


def test_artifacts_directory_fixture_first_round(
        milan_artifacts_directory,
        _milan_artifacts_sub_directories,
):

    assert (
        sorted(os.listdir(milan_artifacts_directory)) ==
        sorted(_milan_artifacts_sub_directories)
    )

    path = os.path.join(milan_artifacts_directory, 'test.txt')

    with open(path, 'w+') as file_handle:
        file_handle.close()


def test_artifacts_directory_fixture_second_round(
        milan_artifacts_directory,
        _milan_artifacts_sub_directories,
):

    assert (
        sorted(os.listdir(milan_artifacts_directory)) ==
        sorted(_milan_artifacts_sub_directories + ['test.txt'])
    )

    path = os.path.join(milan_artifacts_directory, 'test.txt')

    os.unlink(path)
