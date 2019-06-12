from functools import lru_cache

from peewee import fn

from reprobench.core.base import Observer
from reprobench.core.bootstrap.server import bootstrap
from reprobench.core.db import Limit, Run, Step
from reprobench.core.events import (
    BOOTSTRAP,
    RUN_FINISH,
    RUN_INTERRUPT,
    RUN_START,
    RUN_STEP,
    WORKER_JOIN,
)
from reprobench.utils import encode_message


class CoreObserver(Observer):
    SUBSCRIBED_EVENTS = (BOOTSTRAP, WORKER_JOIN, RUN_START, RUN_STEP, RUN_FINISH)

    @classmethod
    @lru_cache(maxsize=1)
    def get_limits(cls):
        return {l.key: l.value for l in Limit.select()}

    @classmethod
    def get_next_pending_run(cls):
        try:
            run = Run.select().where(Run.status == Run.PENDING).limit(1).get()
        except Run.DoesNotExist:
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
            tool=run.tool.module,
            parameters=parameters,
            steps=list(runsteps.dicts()),
            limits=limits,
        )

        return run_dict

    @classmethod
    def get_pending_runs(cls):
        last_step = (
            Step.select(fn.MAX(Step.id)).where(Step.category == Step.RUN).scalar()
        )
        Run.update(status=Run.PENDING).where(
            (Run.status < Run.DONE) | (Run.last_step_id != last_step)
        ).execute()
        pending_runs = Run.select(Run.id).where(Run.status == Run.PENDING).count()
        return pending_runs

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        reply = kwargs.pop("reply")
        address = kwargs.pop("address")
        observe_args = kwargs.pop("observe_args")

        if event_type == BOOTSTRAP:
            bootstrap(observe_args=observe_args, **payload)
            pending_runs = cls.get_pending_runs()
            reply.send_multipart([address, encode_message(pending_runs)])
        elif event_type == WORKER_JOIN:
            run = cls.get_next_pending_run()
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
