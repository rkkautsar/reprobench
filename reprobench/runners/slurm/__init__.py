import click

from reprobench.utils import read_config

from .runner import SlurmRunner


@click.command("slurm")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    show_default=True,
)
@click.option("-w", "--num-workers", type=int, default=4, show_default=True)
@click.option("-p", "--port", default=31313, show_default=True)
@click.option("-r", "--repeat", type=int, default=1)
@click.argument("command", type=click.Choice(("start", "stop", "resume")))
@click.argument("config", type=click.Path(), default="./benchmark.yml")
def cli(command, config, **kwargs):
    config = read_config(config)
    runner = SlurmRunner(config, **kwargs)

    if command == "start":
        runner.start()
    elif command == "stop":
        runner.stop()
    elif command == "resume":
        runner.resume()


if __name__ == "__main__":
    cli()
