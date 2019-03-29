from reprobench.core.db import Run, Step, Limit
from reprobench.core.base import Observer
from reprobench.core.events import (
    RUN_FINISH,
    RUN_START,
    RUN_STEP,
    RUN_INTERRUPT,
    WORKER_REQUEST,
)
from reprobench.utils import encode_message


class CoreObserver(Observer):
    SUBSCRIBED_EVENTS = [WORKER_REQUEST, RUN_START, RUN_STEP, RUN_FINISH]

    @classmethod
    def get_next_pending_run(cls):
        run = Run.get_or_none(Run.status == Run.PENDING)

        if run is None:
            return None

        run.status = Run.SUBMITTED
        run.save()

        runsteps = Step.select().where(Step.category == Step.RUN)
        limits = {l.key: l.value for l in Limit.select()}
        parameters = {p.key: p.value for p in run.parameter_group.parameters}

        run_dict = dict(
            id=run.id,
            task=run.task_id,
            tool=run.tool_id,
            directory=run.directory,
            parameters=parameters,
            steps=list(runsteps.dicts()),
            limits=limits,
        )

        return run_dict

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        reply = kwargs.pop("reply")
        address = kwargs.pop("address")

        if event_type == WORKER_REQUEST:
            run = cls.get_next_pending_run()
            if run is not None:
                reply.send_multipart([address, encode_message(run)])
        elif event_type == RUN_INTERRUPT:
            Run.update(status=Run.PENDING).where(Run.id == payload).execute()
        elif event_type == RUN_START:
            Run.update(status=Run.RUNNING).where(Run.id == payload).execute()
        elif event_type == RUN_STEP:
            step = Step.get(module=payload["step"])
            Run.update(current_step=step).where(Run.id == payload["run_id"]).execute()
        elif event_type == RUN_FINISH:
            Run.update(status=Run.DONE).where(Run.id == payload).execute()
