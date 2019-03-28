import atexit
import platform
from pathlib import Path

import click
import gevent
import zmq.green as zmq
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.core.db import Observer, Run, db
from reprobench.core.events import WORKER_DONE
from reprobench.core.observers import CoreObserver
from reprobench.utils import clean_up, get_db_path, import_class, read_config


class BenchmarkServer:
    BACKEND_ADDRESS = "inproc://backend"

    def __init__(self, db_path, frontend_address, **kwargs):
        super().__init__()
        db.initialize(APSWDatabase(db_path))
        self.frontend_address = frontend_address
        self.observers = [CoreObserver]
        self.observers += [
            import_class(o.module) for o in Observer.select(Observer.module)
        ]
        self.serve_forever = kwargs.pop("forever", False)
        self.jobs_waited = 0

    def loop(self):
        while True:
            if not self.serve_forever and self.jobs_waited == 0:
                break

            address, event_type, payload = self.frontend.recv_multipart()
            logger.trace((address, event_type, payload))
            self.backend.send_multipart([event_type, payload, address])

            if event_type == WORKER_DONE:
                self.jobs_waited -= 1

    def run(self):
        self.context = zmq.Context()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(self.frontend_address)
        self.backend = self.context.socket(zmq.PUB)
        self.backend.bind(self.BACKEND_ADDRESS)

        Run.update(status=Run.PENDING).where(Run.status < Run.DONE).execute()
        self.jobs_waited = Run.select().where(Run.status == Run.PENDING).count()

        logger.info(f"Listening on {self.frontend_address}")

        observer_greenlets = []
        for observer in self.observers:
            greenlet = gevent.spawn(
                observer.observe,
                self.context,
                backend_address=self.BACKEND_ADDRESS,
                reply=self.frontend,
            )
            observer_greenlets.append(greenlet)

        serverlet = gevent.spawn(self.loop)
        serverlet.join()

        gevent.killall(observer_greenlets)


@click.command(name="server")
@click.option("-f", "--forever", help="Serve forever", is_flag=True)
@click.option("-d", "--database", default="./output/benchmark.db", show_default=True)
@click.option("-h", "--host", default="0.0.0.0", show_default=True)
@click.option("-p", "--port", default=31313, show_default=True)
def cli(database, host, port, **kwargs):
    atexit.register(clean_up)

    db_path = str(Path(database).resolve())
    frontend_address = f"tcp://{host}:{port}"
    server = BenchmarkServer(db_path, frontend_address, **kwargs)
    server.run()


if __name__ == "__main__":
    cli()
