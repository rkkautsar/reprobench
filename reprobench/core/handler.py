import msgpack
import zmq.green as zmq
from loguru import logger

from reprobench.core.db import Run
from reprobench.core.events import RUN_FINISH, RUN_REGISTER, RUN_START
from reprobench.utils import decode_message, encode_message, recv_event


def handle_event(context, backend_address, frontend=None):
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.connect(backend_address)

    while True:
        event_type, payload, address = recv_event(socket)
        if event_type == RUN_REGISTER:
            run = Run.get(payload)
            run_dict = dict(
                id=run.id,
                task=run.task_id,
                tool=run.tool_id,
                directory=run.directory,
                parameters=list(run.parameter_group.parameters.dicts()),
            )
            frontend.send_multipart([address, encode_message(run_dict)])
        elif event_type == RUN_START:
            Run.update(status=Run.RUNNING).where(Run.id == payload).execute()
        elif event_type == RUN_FINISH:
            Run.update(status=Run.DONE).where(Run.id == payload).execute()
