import sys
import atexit
import json
from pathlib import Path

import click
import zmq
from sshtunnel import SSHTunnelForwarder
from loguru import logger

from reprobench.console.decorators import common, server_info, use_tunneling
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
    def __init__(self, server_address, tunneling):
        self.server_address = server_address

        if tunneling is not None:
            self.server = SSHTunnelForwarder(
                tunneling["host"],
                remote_bind_address=("127.0.0.1", tunneling["port"]),
                ssh_pkey=tunneling["key_file"],
                ssh_config_file=tunneling["ssh_config_file"],
            )

            # https://github.com/pahaz/sshtunnel/issues/138
            if sys.version_info[0] > 3 or (
                sys.version_info[0] == 3 and sys.version_info[1] >= 7
            ):
                self.server.daemon_forward_servers = True

            self.server.start()
            self.server_address = f"tcp://127.0.0.1:{self.server.local_bind_port}"
            logger.info(f"Tunneling established at {self.server_address}")
            atexit.register(self.stop_tunneling)

    def killed(self, run_id):
        send_event(self.socket, RUN_INTERRUPT, run_id)
        send_event(self.socket, WORKER_LEAVE)

    def stop_tunneling(self):
        self.server.stop()

    def run(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        logger.debug(f"Connecting to {self.server_address}")
        self.socket.connect(self.server_address)

        send_event(self.socket, WORKER_JOIN)
        run = decode_message(self.socket.recv())

        self.run_id = run["id"]
        atexit.register(self.killed, self.run_id)

        tool = import_class(run["tool"])

        if not tool.is_ready():
            tool.setup()

        context = {}
        context["socket"] = self.socket
        context["tool"] = tool
        context["run"] = run
        logger.info(f"Processing task: {run['id']}")

        directory = Path(run["id"])
        directory.mkdir(parents=True, exist_ok=True)

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
        atexit.unregister(self.killed)
        send_event(self.socket, WORKER_LEAVE, self.run_id)


@click.command("worker")
@server_info
@use_tunneling
@common
def cli(**kwargs):
    worker = BenchmarkWorker(**kwargs)
    worker.run()


if __name__ == "__main__":
    cli()
