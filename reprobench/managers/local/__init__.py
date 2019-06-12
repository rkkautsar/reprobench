from multiprocessing import cpu_count

import click
from loguru import logger

from reprobench.console.decorators import server_info, common

from .manager import LocalManager


@click.command("local")
@click.option("-w", "--num-workers", type=int, default=cpu_count(), show_default=True)
@click.option(
    "-d", "--output-dir", type=click.Path(), default="./output", show_default=True
)
@click.option("-r", "--repeat", type=int, default=1)
@click.argument("command", type=click.Choice(("run",)))
@click.argument("config", type=click.Path(), default="./benchmark.yml")
@server_info
@common
def cli(command, **kwargs):
    manager = LocalManager(**kwargs)

    if command == "run":
        manager.run()

    # TODO: add run_with_server


if __name__ == "__main__":
    cli()
