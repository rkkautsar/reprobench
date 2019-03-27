import click

from .local import LocalRunner
from .local import cli as local_cli
from .slurm import SlurmRunner
from .slurm import cli as slurm_cli


@click.group("run")
def cli():
    pass


cli.add_command(local_cli)
cli.add_command(slurm_cli)
