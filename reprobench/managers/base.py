import zmq
from loguru import logger

from reprobench.core.events import BOOTSTRAP
from reprobench.core.bootstrap import bootstrap_client
from reprobench.utils import decode_message, read_config, send_event


class BaseManager(object):
    def __init__(self, server_address, **kwargs):
        self.server_address = server_address
        self.config = kwargs.pop("config")
        self.output_dir = kwargs.pop("output_dir")
        self.repeat = kwargs.pop("repeat")

        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        self.socket.connect(self.server_address)

    def prepare(self):
        pass

    def spawn_workers(self):
        raise NotImplementedError

    def bootstrap(self):
        config = read_config(self.config, resolve_files=True)

        client_results = bootstrap_client(config)
        bootstrapped_config = {**config, **client_results}

        logger.info("Sending bootstrap event to server")
        payload = dict(
            config=bootstrapped_config, output_dir=self.output_dir, repeat=self.repeat
        )
        send_event(self.socket, BOOTSTRAP, payload)

        self.queue = decode_message(self.socket.recv())

    def wait(self):
        pass

    def stop(self):
        pass

    def run(self):
        self.prepare()
        self.bootstrap()
        self.spawn_workers()
        self.wait()
