import atexit
import os
import signal
import time

import click
import strictyaml
import zmq
from loguru import logger

from reprobench.core.schema import schema
from reprobench.runners.local import BenchmarkServer
from reprobench.utils import import_class


def clean_up():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.killpg(os.getpgid(0), signal.SIGTERM)
    time.sleep(1)
    os.killpg(os.getpgid(0), signal.SIGKILL)


@click.command()
@click.option("-c", "--config", required=True, type=click.File())
@click.option(
    "-d",
    "--database",
    required=True,
    type=click.Path(dir_okay=False, resolve_path=True),
)
@click.argument("server_address")
def run(config, database, server_address):
    atexit.register(clean_up)

    config = config.read()
    config = strictyaml.load(config, schema=schema).data
    observers = []
    for observer in config["observers"]:
        observers.append(import_class(observer["module"]))
    server = BenchmarkServer(observers, database, address=server_address)
    server.start()


if __name__ == "__main__":
    run()
