from multiprocessing import cpu_count

import click
from loguru import logger

from reprobench.console.decorators import server_info, common
from reprobench.utils import read_config

from .manager import LocalManager


@click.command("local")
@click.option("-w", "--num-workers", type=int, default=cpu_count(), show_default=True)
@click.argument("command", type=click.Choice(("run",)))
@server_info
@common
def cli(command, **kwargs):
    manager = LocalManager(**kwargs)

    if command == "run":
        manager.run()


if __name__ == "__main__":
    cli()
