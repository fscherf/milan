import logging
import shutil
import os

BACKGROUND_ROOT = os.path.join(
    os.path.dirname(__file__),
    '../frontend/static/background/'
)

logger = logging.getLogger('milan.frontend')


def is_reqular_file(rel_path):
    if rel_path.startswith('.'):
        return False

    if rel_path.startswith('~'):
        return False

    if rel_path.endswith('.swp'):
        return False

    return True


def background_init(cli_args):
    rel_root = os.getcwd()

    if cli_args['directory']:
        rel_root = cli_args['directory']

    abs_root = os.path.abspath(rel_root)

    logging.info('initializing milan background in %s', abs_root)

    # setup root directory
    if not os.path.exists(abs_root):
        logging.debug('creating directory %s', abs_root)

        if not cli_args['dry-run']:
            os.makedirs(abs_root)

    # copy background files
    for rel_src_path in os.listdir(BACKGROUND_ROOT):
        abs_src_path = os.path.join(BACKGROUND_ROOT, rel_src_path)
        abs_dst_path = os.path.join(abs_root, rel_src_path)

        if not is_reqular_file(rel_src_path):
            logging.debug('skipping %s', abs_src_path)

            continue

        logging.debug('copying %s to %s', abs_src_path, abs_dst_path)

        if not cli_args['dry-run']:
            shutil.copy(abs_src_path, abs_dst_path)
