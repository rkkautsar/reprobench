import zmq.green as zmq

from reprobench.utils import recv_event


class Runner:
    def __init__(self, config):
        pass

    def run(self):
        pass


class Observer:
    SUBSCRIBED_EVENTS = []

    @classmethod
    def observe(cls, context, backend_address, frontend):
        socket = context.socket(zmq.SUB)
        socket.connect(backend_address)

        for event in cls.SUBSCRIBED_EVENTS:
            socket.setsockopt(zmq.SUBSCRIBE, event)

        while True:
            event_type, payload, address = recv_event(socket)
            cls.handle_event(event_type, payload, frontend=frontend, address=address)

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        pass


class Step:
    @classmethod
    def register(cls, config={}):
        pass

    @classmethod
    def execute(cls, context, config={}):
        pass


class Tool:
    name = "Base Tool"
    REQUIRED_PATHS = []

    @classmethod
    def setup(cls):
        pass

    @classmethod
    def version(cls):
        return "1.0.0"

    @classmethod
    def pre_run(cls, context):
        pass

    @classmethod
    def cmdline(cls, context):
        pass

    @classmethod
    def post_run(cls, context):
        pass

    @classmethod
    def teardown(cls):
        pass
