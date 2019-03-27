import multiprocessing

import gevent
import zmq.green as zmq
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.core.observer import CoreObserver
from reprobench.core.db import Run, db
from reprobench.core.events import RUN_COMPLETE

BACKEND_ADDRESS = "inproc://backend"


class BenchmarkServer(multiprocessing.Process):
    def __init__(self, observers, db_path, **kwargs):
        super().__init__()
        db.initialize(APSWDatabase(db_path))
        self.frontend_address = kwargs.pop("address", "tcp://*:31334")
        self.observers = observers + [CoreObserver]
        self.jobs_waited = Run.select().where(Run.status < Run.DONE).count()

    def loop(self):
        while True:
            address, event_type, payload = self.frontend.recv_multipart()
            self.backend.send_multipart([event_type, payload, address])
            if event_type == RUN_COMPLETE:
                self.jobs_waited -= 1
            if self.jobs_waited == 0:
                break

    def run(self):
        self.context = zmq.Context()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(self.frontend_address)
        self.backend = self.context.socket(zmq.PUB)
        self.backend.bind(BACKEND_ADDRESS)

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
