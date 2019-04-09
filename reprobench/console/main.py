#!/usr/bin/env python

import click

from reprobench.core.bootstrap import cli as bootstrap_cli

from .status import benchmark_status


@click.group()
@click.version_option()
def cli():
    pass


cli.add_command(bootstrap_cli)

try:
    from reprobench.core.server import cli as server_cli

    cli.add_command(server_cli)
    cli.add_command(benchmark_status)
except ImportError:
    pass

try:
    from reprobench.core.worker import cli as worker_cli

    cli.add_command(worker_cli)
except ImportError:
    pass

try:
    from reprobench.managers import cli as manager_cli

    cli.add_command(manager_cli)
except ImportError:
    pass

try:
    from reprobench.core.analyzer import cli as analyzer_cli

    cli.add_command(analyzer_cli)
except ImportError:
    pass


if __name__ == "__main__":
    cli()
