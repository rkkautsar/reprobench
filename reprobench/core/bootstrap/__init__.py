import click
import zmq
from loguru import logger
from reprobench.console.decorators import common, server_info
from reprobench.core.events import BOOTSTRAP
from reprobench.utils import read_config, send_event

from .client import bootstrap as bootstrap_client


@click.command(name="bootstrap")
@click.option("-r", "--repeat", type=int, default=1)
@click.option(
    "-d",
    "--output-dir",
    type=click.Path(),
    default="./output",
    required=True,
    show_default=True,
)
@click.argument("config", type=click.Path(), default="./benchmark.yml")
@server_info
@common
def cli(server_address, config, output_dir, **kwargs):
    config = read_config(config, resolve_files=True)

    client_results = bootstrap_client(config)
    bootstrapped_config = { **config, **client_results }

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(server_address)
    payload = dict(config=bootstrapped_config, output_dir=output_dir, **kwargs)

    logger.info("Sending bootstrap event to server")
    send_event(socket, BOOTSTRAP, payload)


if __name__ == "__main__":
    cli()
