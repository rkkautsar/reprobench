import functools
import os
import sys
from pathlib import Path

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


def use_tunneling(func):
    @click.option("-h", "--host", required=False, help="[Tunneling] SSH Host")
    @click.option(
        "-p", "--port", help="[Tunneling] Remote server port for", default=31313
    )
    @click.option(
        "-K",
        "--key-file",
        type=click.Path(exists=True),
        help="[Tunneling] SSH private key file",
        required=False,
    )
    @click.option(
        "-C",
        "--ssh-config-file",
        help="[Tunneling] SSH config file",
        default=Path.home() / ".ssh" / "config",
    )
    @functools.wraps(func)
    def wrapper(host, port, key_file, ssh_config_file, *args, **kwargs):
        if host is not None:
            tunneling = dict(
                host=host, port=port, key_file=key_file, ssh_config_file=ssh_config_file
            )
            return func(tunneling=tunneling, *args, **kwargs)

        return func(tunneling=None, *args, **kwargs)

    return wrapper
