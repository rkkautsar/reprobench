from pathlib import Path

import zmq
from loguru import logger

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.events import SERVER_PING
from reprobench.utils import get_db_path, send_event

PREVIOUS_RUN_EXIST_MSG = f"""
Previous run exists in the specified output directory.
Please use resume instead, or specify a different output directory.
"""

OUTDIR_NOT_EXIST_MSG = f"""
No benchmark in the specified output directory.
Please use start to also create the output directory.
"""


class BaseRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir")
        self.repeat = kwargs.pop("repeat", 1)
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

        send_event(socket, SERVER_PING)
        socket.recv()

    def wait(self):
        pass

    def start(self):
        db_exist = Path(self.db_path).exists()

        if db_exist:
            logger.error(PREVIOUS_RUN_EXIST_MSG)
            exit(1)

        bootstrap(self.config, self.output_dir, repeat=self.repeat)
        self.run()

    def stop(self):
        pass

    def resume(self):
        db_exist = Path(self.db_path).exists()

        if not db_exist:
            logger.error(OUTDIR_NOT_EXIST_MSG)
            exit(1)

        self.run()

    def run(self):
        self.prepare()
        self.spawn_server()
        logger.info("Making sure the server has started...")
        self.server_ping()
        self.spawn_workers()
        self.wait()
