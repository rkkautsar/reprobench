import click

from .local import LocalManager
from .local import cli as local_cli
from .slurm import SlurmManager
from .slurm import cli as slurm_cli


@click.group("manage")
def cli():
    pass


cli.add_command(local_cli)
cli.add_command(slurm_cli)
