#!/usr/bin/env python

import argparse
import os
import sys

import click
import strictyaml
from loguru import logger

from reprobench.core.bootstrap import cli as bootstrap_cli
from reprobench.core.server import cli as server_cli
from reprobench.core.schema import schema
from reprobench.utils import import_class, read_config

from reprobench.runners import cli as runner_cli


@click.group()
@click.version_option()
@click.option("--verbose", "-v", "verbosity", count=True, default=0, help="Verbosity")
def cli(verbosity):
    sys.path.append(os.getcwd())
    logger.remove()

    if verbosity == 0:
        logger.add(sys.stderr, level="ERROR")
    elif verbosity == 1:
        logger.add(sys.stderr, level="WARNING")
    elif verbosity == 2:
        logger.add(sys.stderr, level="INFO")
    elif verbosity == 3:
        logger.add(sys.stderr, level="DEBUG")
    elif verbosity >= 4:
        logger.add(sys.stderr, level="TRACE")


cli.add_command(bootstrap_cli)
cli.add_command(server_cli)
cli.add_command(runner_cli)


if __name__ == "__main__":
    cli()
