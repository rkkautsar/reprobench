from pathlib import Path

import click
import gevent
import zmq.green as zmq
from loguru import logger
from reprobench.console.decorators import common, server_info
from reprobench.core.bootstrap.server import bootstrap
from reprobench.core.db import Observer
from reprobench.core.events import BOOTSTRAP
from reprobench.core.observers import CoreObserver
from reprobench.utils import decode_message, import_class


class BenchmarkServer(object):
    BACKEND_ADDRESS = "inproc://backend"

    def __init__(self, frontend_address, **kwargs):
        self.frontend_address = frontend_address

    def receive_event(self):
        address, event_type, payload = self.frontend.recv_multipart()
        logger.trace((address, event_type, decode_message(payload)))
        return address, event_type, payload

    def loop(self):
        while True:
            address, event_type, payload = self.receive_event()
            self.backend.send_multipart([event_type, payload, address])

    def run(self):
        self.context = zmq.Context()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(self.frontend_address)
        self.backend = self.context.socket(zmq.PUB)
        self.backend.bind(self.BACKEND_ADDRESS)

        core_observer_greenlet = gevent.spawn(
            CoreObserver.observe,
            self.context,
            backend_address=self.BACKEND_ADDRESS,
            reply=self.frontend,
        )
        logger.info(f"Listening on {self.frontend_address}...")

        serverlet = gevent.spawn(self.loop)
        logger.info(f"Ready to receive events...")
        serverlet.join()
        core_observer_greenlet.kill()


@click.command(name="server")
@server_info
@common
def cli(server_address, **kwargs):
    server = BenchmarkServer(server_address, **kwargs)
    server.run()


if __name__ == "__main__":
    cli()
