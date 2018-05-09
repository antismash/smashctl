"""Command line handling"""

import argparse
from envparse import Env

from . import __version__
from .common import run_command
from .storage import get_storage
from . import job


def main():
    """Run smashctl"""

    env = Env(
        # Redis DB to contact
        SMASHCTL_REDIS=dict(cast=str, default='redis://localhost:6379/0'),
        SMASHCTL_BASEURL=dict(cast=str, default='https://antismash/secondarymetabolites.org/'),
    )

    parser = argparse.ArgumentParser(prog='smashctl')
    parser.add_argument('--db', default=env('SMASHCTL_REDIS'),
                        help="Redis database to contact (default: %(default)s)")
    parser.add_argument('-V', '--version', action='version', version=__version__)

    subparsers = parser.add_subparsers(title='subcommands')
    job.register(subparsers)

    args = parser.parse_args()
    store = get_storage(args.db)
    run_command(args.func, args, store)


if __name__ == '__main__':
    main()
