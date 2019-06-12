import click

from reprobench.console.decorators import common, server_info
from reprobench.utils import read_config

from .manager import SlurmManager


@click.command("slurm")
@click.option(
    "-d", "--output-dir", type=click.Path(), default="./output", show_default=True
)
@click.option("-r", "--repeat", type=int, default=1)
@click.argument("command", type=click.Choice(("run", "stop")))
@click.argument("config", type=click.Path(), default="./benchmark.yml")
@server_info
@common
def cli(command, **kwargs):
    manager = SlurmManager(**kwargs)

    if command == "run":
        manager.run()
    elif command == "stop":
        manager.stop()


if __name__ == "__main__":
    cli()
