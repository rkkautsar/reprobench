#!/usr/bin/env python

import argparse
import os
import sys

import click
from loguru import logger

from reprobench.core.bootstrap import cli as bootstrap_cli
from reprobench.core.server import cli as server_cli
from reprobench.core.worker import cli as worker_cli
from reprobench.utils import import_class

from reprobench.runners import cli as runner_cli


@click.group()
@click.version_option()
@click.option("-q", "--quiet", is_flag=True)
@click.option("--verbose", "-v", "verbosity", count=True, default=0, help="Verbosity")
def cli(quiet, verbosity):
    sys.path.append(os.getcwd())
    logger.remove()

    if not quiet:
        verbosity_levels = ["INFO", "DEBUG", "TRACE"]
        verbosity = min(verbosity, 2)
        logger.add(sys.stderr, level=verbosity_levels[verbosity])


cli.add_command(bootstrap_cli)
cli.add_command(server_cli)
cli.add_command(runner_cli)
cli.add_command(worker_cli)


if __name__ == "__main__":
    cli()
