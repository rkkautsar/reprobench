import zmq
from loguru import logger

from reprobench.core.events import BOOTSTRAP
from reprobench.core.bootstrap import bootstrap_client
from reprobench.utils import decode_message, read_config, send_event


class BaseManager(object):
    def __init__(self, config, server_address, tunneling, **kwargs):
        self.server_address = server_address
        self.tunneling = tunneling
        self.config = read_config(config, resolve_files=True)
        self.output_dir = kwargs.pop("output_dir")
        self.repeat = kwargs.pop("repeat")

        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)

    def prepare(self):
        pass

    def spawn_workers(self):
        raise NotImplementedError

    def bootstrap(self):
        self.socket.connect(self.server_address)

        client_results = bootstrap_client(self.config)
        bootstrapped_config = {**self.config, **client_results}

        logger.info("Sending bootstrap event to server")
        payload = dict(
            config=bootstrapped_config, output_dir=self.output_dir, repeat=self.repeat
        )
        send_event(self.socket, BOOTSTRAP, payload)

        self.pending = decode_message(self.socket.recv())

    def wait(self):
        pass

    def stop(self):
        pass

    def run(self):
        self.prepare()
        self.bootstrap()
        self.spawn_workers()
        self.wait()
