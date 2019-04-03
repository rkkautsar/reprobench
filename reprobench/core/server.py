from pathlib import Path

import click
import gevent
import zmq.green as zmq
from loguru import logger
from playhouse.apsw_ext import APSWDatabase, fn

from reprobench.core.db import Observer, Run, Step, db
from reprobench.core.events import WORKER_JOIN, WORKER_LEAVE, RUN_FINISH, SERVER_PING
from reprobench.core.observers import CoreObserver
from reprobench.utils import import_class


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
        self.worker_count = 0
        self.pinged = False

    def loop(self):
        while True:
            if (
                not self.serve_forever
                and self.jobs_waited == 0
                and self.worker_count == 0
                and self.pinged
            ):
                logger.success("No more work for the workers.")
                break

            address, event_type, payload = self.frontend.recv_multipart()
            logger.trace((address, event_type, payload))
            self.backend.send_multipart([event_type, payload, address])

            if event_type == SERVER_PING:
                self.frontend.send_multipart([address, b"pong"])
                self.pinged = True
            elif event_type == WORKER_JOIN:
                self.worker_count += 1
            elif event_type == WORKER_LEAVE:
                self.worker_count -= 1
            elif event_type == RUN_FINISH:
                self.jobs_waited -= 1

    def run(self):
        self.context = zmq.Context()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(self.frontend_address)
        self.backend = self.context.socket(zmq.PUB)
        self.backend.bind(self.BACKEND_ADDRESS)

        last_step = Step.select(fn.MAX(Step.id)).scalar()
        Run.update(status=Run.PENDING).where(
            (Run.status < Run.DONE) | (Run.last_step_id != last_step)
        ).execute()
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
    db_path = str(Path(database).resolve())
    frontend_address = f"tcp://{host}:{port}"
    server = BenchmarkServer(db_path, frontend_address, **kwargs)
    server.run()


if __name__ == "__main__":
    cli()
