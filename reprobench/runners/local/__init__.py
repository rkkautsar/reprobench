from multiprocessing import cpu_count

import click
from loguru import logger

from reprobench.utils import read_config

from .runner import LocalRunner


@click.command("local")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    show_default=True,
)
@click.option("-w", "--num-workers", type=int, default=cpu_count(), show_default=True)
@click.option("-h", "--host", default="127.0.0.1", show_default=True)
@click.option("-p", "--port", default=31313, show_default=True)
@click.option("-r", "--repeat", type=int, default=1)
@click.argument("command", type=click.Choice(("start", "resume")))
@click.argument("config", type=click.Path(), default="./benchmark.yml")
def cli(command, config, **kwargs):
    config = read_config(config)
    runner = LocalRunner(config, **kwargs)

    if command == "start":
        runner.start()
    else:
        runner.resume()


if __name__ == "__main__":
    cli()
