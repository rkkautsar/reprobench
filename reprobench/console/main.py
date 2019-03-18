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
@click.version_option(version="0.1.0")
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
    required=True,
    show_default=True,
)
@click.option("-r", "--resume", is_flag=True)
@click.argument("config", type=click.File("r"))
def local_runner(output_dir, resume, config):
    config_text = config.read()
    config = strictyaml.load(config_text, schema=schema).data
    runner = LocalRunner(config, output_dir, resume)
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
@click.argument("config", type=click.File("r"))
def slurm_runner(
    output_dir, run_template, compile_template, resume, teardown, python_path, config
):
    config_path = os.path.realpath(config.name)
    config_text = config.read()
    config = strictyaml.load(config_text, schema=schema).data
    runner = SlurmRunner(
        config=config,
        run_template_file=run_template,
        compile_template_file=compile_template,
        config_path=config_path,
        output_dir=output_dir,
        resume=resume,
        teardown=teardown,
        python_path=python_path,
    )
    runner.run()


if __name__ == "__main__":
    cli()
