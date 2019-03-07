#!/usr/bin/env python

import argparse
from loguru import logger
import sys
import strictyaml
import click

from reprobench.core.schema import schema
from reprobench.utils import import_class

from reprobench.runners import LocalRunner


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", "verbosity", count=True, default=0, help="Verbosity")
def cli(verbosity):
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


@cli.group()
def run():
    pass


@run.command("local")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    show_default=True,
)
@click.option("-r", "--resume", is_flag=True)
@click.argument("config", type=click.File("r"))
def local_runner(output_dir, resume, config):
    config_text = config.read()
    config = strictyaml.load(config_text, schema=schema).data
    runner = LocalRunner(config, output_dir, resume)
    runner.run()


if __name__ == "__main__":
    cli()
