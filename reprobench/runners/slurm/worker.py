import atexit
import os
import signal
import time

import click
import zmq
from loguru import logger

from reprobench.core.schema import schema
from reprobench.runners.local.worker import RUN_REGISTER
from reprobench.utils import (
    clean_up,
    decode_message,
    import_class,
    send_event,
    read_config,
)


@click.command()
@click.option("-c", "--config", required=True, type=click.Path())
@click.argument("server_address")
@click.argument("run_id", type=int)
def run(config, server_address, run_id):
    atexit.register(clean_up)

    config = read_config(config)

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(server_address)
    send_event(socket, RUN_REGISTER, run_id)
    run = decode_message(socket.recv())

    tool = import_class(run["tool"])
    context = config.copy()
    context["socket"] = socket
    context["tool"] = tool
    context["run"] = run
    logger.info(f"Processing task: {run['directory']}")

    for runstep in config["steps"]["run"]:
        logger.debug(f"Running step {runstep['module']}")
        step = import_class(runstep["module"])
        step.execute(context, runstep.get("config", {}))


if __name__ == "__main__":
    run()
