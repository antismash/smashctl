"""Common functions"""
import argparse
import sys
from typing import Callable

from redis import Redis

from .storage import AntismashStorageError


CommandFunc = Callable[[argparse.Namespace, Redis], str]


class AntismashRunError(RuntimeError):
    """Generic error thrown by the command line"""
    pass


def run_command(func, args, storage):
    """Run a smashctl command

    :param func: Function to run
    :param args: Namespace object with command line args
    :param storage: A Redis instance connected to the database
    """

    try:
        print(func(args, storage))
    except (AntismashRunError, AntismashStorageError) as e:
        print("ERROR: ", e, file=sys.stderr)
        sys.exit(1)


def default_action(func: CommandFunc, **kwargs) -> CommandFunc:
    def new_func(args: argparse.Namespace, storage: Redis) -> str:
        for name, value in kwargs.items():
            setattr(args, name, value)
        return func(args, storage)
    return new_func
