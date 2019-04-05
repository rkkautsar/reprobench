import zmq

from reprobench.core.events import REQUEST_PENDING
from reprobench.utils import send_event, decode_message


class BaseManager(object):
    def __init__(self, server_address, **kwargs):
        self.server_address = server_address
        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        self.socket.connect(self.server_address)

    def prepare(self):
        pass

    def spawn_workers(self):
        raise NotImplementedError

    def get_pending_runs(self):
        send_event(self.socket, REQUEST_PENDING)
        self.queue = decode_message(self.socket.recv())

    def wait(self):
        pass

    def stop(self):
        pass

    def run(self):
        self.prepare()
        self.get_pending_runs()
        self.spawn_workers()
        self.wait()
