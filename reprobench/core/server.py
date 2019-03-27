import atexit
import multiprocessing

import click
import gevent
import strictyaml
import zmq.green as zmq
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.core.db import Run, db
from reprobench.core.events import RUN_COMPLETE
from reprobench.core.observers import CoreObserver
from reprobench.core.schema import schema
from reprobench.utils import clean_up, get_db_path, import_class, read_config

BACKEND_ADDRESS = "inproc://backend"


class BenchmarkServer:
    def __init__(self, observers, db_path, **kwargs):
        super().__init__()
        db.initialize(APSWDatabase(db_path))
        self.frontend_address = kwargs.pop("address", "tcp://*:31334")
        self.serve_forever = kwargs.pop("forever", False)
        self.observers = observers + [CoreObserver]
        self.jobs_waited = Run.select().where(Run.status < Run.DONE).count()

    def loop(self):
        while True:
            address, event_type, payload = self.frontend.recv_multipart()
            logger.debug((address, event_type, payload))
            self.backend.send_multipart([event_type, payload, address])
            if event_type == RUN_COMPLETE:
                self.jobs_waited -= 1
            if not self.serve_forever and self.jobs_waited == 0:
                break

    def run(self):
        self.context = zmq.Context()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(self.frontend_address)
        self.backend = self.context.socket(zmq.PUB)
        self.backend.bind(BACKEND_ADDRESS)

        logger.info(f"Listening on {self.frontend_address}")

        observer_greenlets = []
        for observer in self.observers:
            greenlet = gevent.spawn(
                observer.observe,
                self.context,
                backend_address=BACKEND_ADDRESS,
                frontend=self.frontend,
            )
            observer_greenlets.append(greenlet)

        serverlet = gevent.spawn(self.loop)
        serverlet.join()

        gevent.killall(observer_greenlets)


@click.command(name="server")
@click.option("-c", "--config", required=True, type=click.Path())
@click.option("-f", "--forever", help="Serve forever", is_flag=True)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    required=True,
    show_default=True,
)
@click.argument("server_address")
def cli(config, output_dir, server_address):
    atexit.register(clean_up)

    config = read_config(config)
    database = get_db_path(output_dir)

    observers = []
    for observer in config["observers"]:
        observers.append(import_class(observer["module"]))

    server = BenchmarkServer(observers, database, address=server_address)
    server.run()


if __name__ == "__main__":
    cli()
