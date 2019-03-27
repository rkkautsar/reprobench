#!/usr/bin/env python

import os
import argparse
import sys
import strictyaml
import click
from loguru import logger

from reprobench.core.schema import schema
from reprobench.utils import import_class

from reprobench.runners import LocalRunner, SlurmRunner


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
@click.option("-s", "--server", default="tcp://127.0.0.1:31313")
@click.argument("config", type=click.File("r"))
def local_runner(config, output_dir, server, **kwargs):
    config_text = config.read()
    config = strictyaml.load(config_text, schema=schema).data
    runner = LocalRunner(config, output_dir=output_dir, server_address=server, **kwargs)
    runner.run()


@run.command("slurm")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    required=True,
    show_default=True,
)
@click.option("--run-template", type=click.Path(dir_okay=False, resolve_path=True))
@click.option("--compile-template", type=click.Path(dir_okay=False, resolve_path=True))
@click.option("-r", "--resume", is_flag=True)
@click.option("-d", "--teardown", is_flag=True)
@click.option("-p", "--python-path", required=True)
@click.option("-s", "--server", required=True)
@click.argument("config", type=click.File("r"))
def slurm_runner(config, output_dir, python_path, server, **kwargs):
    config_path = os.path.realpath(config.name)
    config_text = config.read()
    config = strictyaml.load(config_text, schema=schema).data
    runner = SlurmRunner(
        config=config,
        config_path=config_path,
        python_path=python_path,
        server_address=server,
        **kwargs
    )
    runner.run()


if __name__ == "__main__":
    cli()
