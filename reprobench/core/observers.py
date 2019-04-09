from functools import lru_cache

from peewee import fn

from reprobench.core.base import Observer
from reprobench.core.update import update
from reprobench.core.db import Limit, Run, Step
from reprobench.core.events import (
    BOOTSTRAP,
    REQUEST_PENDING,
    RUN_FINISH,
    RUN_INTERRUPT,
    RUN_START,
    RUN_STEP,
    WORKER_JOIN,
)
from reprobench.utils import encode_message


class CoreObserver(Observer):
    SUBSCRIBED_EVENTS = (
        BOOTSTRAP,
        WORKER_JOIN,
        RUN_START,
        RUN_STEP,
        RUN_FINISH,
        REQUEST_PENDING,
    )

    @classmethod
    @lru_cache(maxsize=1)
    def get_limits(cls):
        return {l.key: l.value for l in Limit.select()}

    @classmethod
    def get_run(cls, run_id):
        run = Run.get_by_id(run_id)

        if run is None:
            return None

        run.status = Run.SUBMITTED
        run.save()

        last_step = run.last_step_id or 0

        runsteps = Step.select().where(
            (Step.category == Step.RUN) & (Step.id > last_step)
        )
        limits = cls.get_limits()
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
    def get_pending_run_ids(cls):
        last_step = (
            Step.select(fn.MAX(Step.id)).where(Step.category == Step.RUN).scalar()
        )
        Run.update(status=Run.PENDING).where(
            (Run.status < Run.DONE) | (Run.last_step_id != last_step)
        ).execute()
        pending_runs = Run.select(Run.id).where(Run.status == Run.PENDING)
        return [r.id for r in pending_runs]

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        reply = kwargs.pop("reply")
        address = kwargs.pop("address")

        if event_type == BOOTSTRAP:
            update(**payload)
        elif event_type == REQUEST_PENDING:
            run_ids = cls.get_pending_run_ids()
            reply.send_multipart([address, encode_message(run_ids)])
        elif event_type == WORKER_JOIN:
            run = cls.get_run(payload)
            reply.send_multipart([address, encode_message(run)])
        elif event_type == RUN_INTERRUPT:
            Run.update(status=Run.PENDING).where(Run.id == payload).execute()
        elif event_type == RUN_START:
            run_id = payload.pop("run_id")
            Run.update(status=Run.RUNNING, **payload).where(Run.id == run_id).execute()
        elif event_type == RUN_STEP:
            step = Step.get(module=payload["step"])
            Run.update(last_step=step).where(Run.id == payload["run_id"]).execute()
        elif event_type == RUN_FINISH:
            Run.update(status=Run.DONE).where(Run.id == payload).execute()
