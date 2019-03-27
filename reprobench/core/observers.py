from reprobench.core.db import Run
from reprobench.core.base import Observer
from reprobench.core.events import RUN_FINISH, RUN_REGISTER, RUN_START
from reprobench.utils import encode_message


class CoreObserver(Observer):
    SUBSCRIBED_EVENTS = [RUN_REGISTER, RUN_START, RUN_FINISH]

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        frontend = kwargs.pop("frontend")
        address = kwargs.pop("address")

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
