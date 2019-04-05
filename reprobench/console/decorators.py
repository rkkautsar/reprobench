import functools
import os
import sys

import click
from loguru import logger


def common(func):
    @click.option("-q", "--quiet", is_flag=True)
    @click.option(
        "--verbose", "-v", "verbosity", count=True, default=0, help="Verbosity"
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        quiet = kwargs.pop("quiet")
        verbosity = kwargs.pop("verbosity")

        sys.path.append(os.getcwd())
        logger.remove()

        if not quiet:
            verbosity_levels = ["INFO", "DEBUG", "TRACE"]
            verbosity = min(verbosity, 2)
            logger.add(sys.stderr, level=verbosity_levels[verbosity])

        return func(*args, **kwargs)

    return wrapper


def server_info(func):
    @click.option("-a", "--address", default="tcp://127.0.0.1:31313", show_default=True)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        server_address = kwargs.pop("address")
        return func(server_address=server_address, *args, **kwargs)

    return wrapper
