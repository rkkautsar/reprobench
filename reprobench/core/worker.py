import atexit
import json
from pathlib import Path

import click
import zmq
from loguru import logger

from reprobench.console.decorators import common, server_info
from reprobench.core.events import (
    RUN_FINISH,
    RUN_INTERRUPT,
    RUN_START,
    RUN_STEP,
    WORKER_JOIN,
    WORKER_LEAVE,
)
from reprobench.utils import decode_message, import_class, send_event

REQUEST_TIMEOUT = 15000


class BenchmarkWorker:
    def __init__(self, server_address, run_id):
        self.server_address = server_address
        self.run_id = run_id

    def killed(self, run_id):
        send_event(self.socket, RUN_INTERRUPT, run_id)
        send_event(self.socket, WORKER_LEAVE)

    def run(self):
        atexit.register(self.killed, self.run_id)

        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        self.socket.connect(self.server_address)

        send_event(self.socket, WORKER_JOIN, self.run_id)
        run = decode_message(self.socket.recv())

        tool = import_class(run["tool"])

        context = {}
        context["socket"] = self.socket
        context["tool"] = tool
        context["run"] = run
        logger.info(f"Processing task: {run['directory']}")
        Path(run["directory"]).mkdir(parents=True, exist_ok=True)

        payload = dict(tool_version=tool.version(), run_id=self.run_id)
        send_event(self.socket, RUN_START, payload)

        for runstep in run["steps"]:
            logger.debug(f"Running step {runstep['module']}")
            step = import_class(runstep["module"])
            config = json.loads(runstep["config"])
            step.execute(context, config)
            payload = {"run_id": self.run_id, "step": runstep["module"]}
            send_event(self.socket, RUN_STEP, payload)

        send_event(self.socket, RUN_FINISH, self.run_id)
        send_event(self.socket, WORKER_LEAVE, self.run_id)


@click.command("worker")
@click.argument("run_id")
@common
@server_info
def cli(server_address, run_id):
    worker = BenchmarkWorker(server_address, run_id)
    worker.run()


if __name__ == "__main__":
    cli()
