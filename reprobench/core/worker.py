import atexit
import json

import click
import zmq
from loguru import logger

from reprobench.core.events import (
    WORKER_JOIN,
    WORKER_REQUEST,
    WORKER_LEAVE,
    RUN_START,
    RUN_STEP,
    RUN_FINISH,
    RUN_INTERRUPT,
)
from reprobench.utils import decode_message, import_class, send_event


REQUEST_TIMEOUT = 15000


class BenchmarkWorker:
    """
    Request for a work from server,
    if there's no more work, terminate.
    else, do the work and request for more.
    """

    def __init__(self, server_address):
        self.server_address = server_address

    def killed(self, run_id):
        send_event(self.socket, RUN_INTERRUPT, run_id)
        send_event(self.socket, WORKER_LEAVE)

    def loop(self):
        while True:
            send_event(self.socket, WORKER_REQUEST)

            reply_count = self.socket.poll(timeout=REQUEST_TIMEOUT)
            if reply_count == 0:
                # looks like the server is dead
                logger.warning("Exiting because there's no reply from server.")
                break

            run = decode_message(self.socket.recv())

            if run is None:
                # there's no more work to do
                logger.success("Exiting because there's no more work to do.")
                break

            atexit.register(self.killed, run["id"])
            tool = import_class(run["tool"])

            context = {}
            context["socket"] = self.socket
            context["tool"] = tool
            context["run"] = run
            logger.info(f"Processing task: {run['directory']}")

            run_id = run["id"]

            send_event(
                self.socket,
                RUN_START,
                {"tool_version": tool.version(), "run_id": run_id},
            )

            for runstep in run["steps"]:
                logger.debug(f"Running step {runstep['module']}")
                step = import_class(runstep["module"])
                config = json.loads(runstep["config"])
                step.execute(context, config)
                payload = {"run_id": run_id, "step": runstep["module"]}
                send_event(self.socket, RUN_STEP, payload)

            send_event(self.socket, RUN_FINISH, run_id)

            atexit.unregister(self.killed)

    def run(self):
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
