from reprobench.core.base import Step, Observer
from reprobench.executors.events import STORE_RUNSTATS

from .db import RunStatistic


class RunStatisticObserver(Observer):
    SUBSCRIBED_EVENTS = (STORE_RUNSTATS,)

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        if event_type == STORE_RUNSTATS:
            RunStatistic.create(**payload)


class Executor(Step):
    def __init__(self, *args, **kwargs):
        pass

    def run(
        self,
        cmdline,
        out_path=None,
        err_path=None,
        input_str=None,
        directory=None,
        **kwargs
    ):
        raise NotImplementedError

    @classmethod
    def register(cls, config=None):
        RunStatistic.create_table()

    @classmethod
    def execute(cls, context, config=None):
        tool = context["tool"]
        executor = cls(context, config)
        tool(context).run(executor)
