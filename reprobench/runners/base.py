import time
from pathlib import Path

import zmq
from loguru import logger

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.events import SERVER_PING
from reprobench.utils import get_db_path, send_event


class BaseRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir")
        self.resume = kwargs.pop("resume", False)
        self.num_workers = kwargs.pop("num_workers", None)
        self.db_path = get_db_path(self.output_dir)
        self.server_address = None

    def prepare(self):
        pass

    def spawn_server(self):
        raise NotImplementedError

    def spawn_workers(self):
        raise NotImplementedError

    def server_ping(self):
        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        socket.connect(self.server_address)

        # should be blocking if not ready: http://api.zeromq.org/2-1:zmq-socket
        send_event(socket, SERVER_PING)
        socket.recv()

    def wait(self):
        pass

    def run(self):
        db_exist = Path(self.db_path).exists()

        if not db_exist:
            bootstrap(self.config, self.output_dir)

        if db_exist and not self.resume:
            logger.warning(
                f"Previous run exists in {self.output_dir}. Please use --resume, or specify a different output directory"
            )
            exit(1)

        self.prepare()
        self.spawn_server()
        logger.info("Making sure the server has started...")
        self.server_ping()
        self.spawn_workers()
        self.wait()
