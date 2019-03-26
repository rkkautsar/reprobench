import multiprocessing

import gevent
import zmq.green as zmq
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

import reprobench.core.handler as core_handler
from reprobench.core.db import Run, db
from reprobench.core.events import RUN_COMPLETE

BACKEND_ADDRESS = "inproc://backend"


class BenchmarkServer(multiprocessing.Process):
    def __init__(self, handlers, db_path, jobs_waited, **kwargs):
        super().__init__()
        db.initialize(APSWDatabase(db_path))
        self.frontend_address = kwargs.pop("address", "tcp://*:31334")
        self.handlers = handlers + [core_handler]
        self.jobs_waited = jobs_waited

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

        greenlets = []
        for handler in self.handlers:
            greenlet = gevent.spawn(
                handler.handle_event,
                self.context,
                backend_address=BACKEND_ADDRESS,
                frontend=self.frontend,
            )
            greenlets.append(greenlet)

        serverlet = gevent.spawn(self.loop)
        serverlet.join()

        gevent.killall(greenlets)
