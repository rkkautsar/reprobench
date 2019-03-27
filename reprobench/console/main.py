#!/usr/bin/env python

import argparse
import os
import sys

import click
from loguru import logger

from reprobench.core.bootstrap import cli as bootstrap_cli
from reprobench.core.server import cli as server_cli
from reprobench.utils import import_class

from reprobench.runners import cli as runner_cli


@click.group()
@click.version_option()
@click.option("--verbose", "-v", "verbosity", count=True, default=0, help="Verbosity")
def cli(verbosity):
    sys.path.append(os.getcwd())
    logger.remove()
    verbosity_levels = ["ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]
    verbosity = max(verbosity, 4)
    logger.add(sys.stderr, level=verbosity_levels[verbosity])


cli.add_command(bootstrap_cli)
cli.add_command(server_cli)
cli.add_command(runner_cli)


if __name__ == "__main__":
    cli()
