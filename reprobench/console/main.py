#!/usr/bin/env python

import click

from reprobench.core.bootstrap import cli as bootstrap_cli
from reprobench.core.server import cli as server_cli
from reprobench.core.worker import cli as worker_cli
from reprobench.managers import cli as manager_cli

from .status import benchmark_status


@click.group()
@click.version_option()
def cli():
    pass


cli.add_command(bootstrap_cli)
cli.add_command(server_cli)
cli.add_command(worker_cli)
cli.add_command(manager_cli)
cli.add_command(benchmark_status)


if __name__ == "__main__":
    cli()
