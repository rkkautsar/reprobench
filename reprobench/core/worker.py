import atexit
import json
import multiprocessing

import click
import tqdm
import zmq
from loguru import logger

from reprobench.core.events import (
    WORKER_JOIN,
    WORKER_REQUEST,
    WORKER_DONE,
    WORKER_LEAVE,
    RUN_STEP,
)
from reprobench.utils import clean_up, decode_message, import_class, send_event


class BenchmarkWorker:
    """
    Request for a work from server,
    if there's no more work, terminate.
    else, do the work and request for more.
    """

    def __init__(self, server_address):
        self.server_address = server_address

    def loop(self):

        while True:
            send_event(self.socket, WORKER_REQUEST)

            reply_count = self.socket.poll(timeout=3000)
            if reply_count == 0:
                # looks like the server is dead
                break

            run = decode_message(self.socket.recv())

            if run is None:
                # there's no more work to do
                break

            tool = import_class(run["tool"])
            if not tool.is_ready():
                tool.setup()

            context = {}
            context["socket"] = self.socket
            context["tool"] = tool
            context["run"] = run
            logger.info(f"Processing task: {run['directory']}")

            for runstep in run["steps"]:
                payload = {"run_id": run["id"], "step": runstep["module"]}
                send_event(self.socket, RUN_STEP, payload)
                logger.debug(f"Running step {runstep['module']}")
                step = import_class(runstep["module"])
                config = json.loads(runstep["config"])
                step.execute(context, config)
            send_event(self.socket, WORKER_DONE, run["id"])

    def run(self):
        atexit.register(clean_up)

        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        self.socket.connect(self.server_address)

        send_event(self.socket, WORKER_JOIN)
        self.loop()
        send_event(self.socket, WORKER_LEAVE)


@click.command("worker")
@click.option("-h", "--host", default="0.0.0.0", show_default=True)
@click.option("-p", "--port", default=31313, show_default=True)
def cli(host, port):
    worker = BenchmarkWorker(f"tcp://{host}:{port}")
    worker.run()


if __name__ == "__main__":
    cli()
