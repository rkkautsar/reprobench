from loguru import logger

from reprobench.core.base import Step, Observer
from reprobench.executors.events import STORE_RUNSTATS
from reprobench.utils import recv_event

from .db import RunStatistic


class RunStatisticObserver(Observer):
    SUBSCRIBED_EVENTS = [STORE_RUNSTATS]

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        if event_type == STORE_RUNSTATS:
            RunStatistic.create(**payload)


class Executor(Step):
    @classmethod
    def register(cls, config={}):
        RunStatistic.create_table()
