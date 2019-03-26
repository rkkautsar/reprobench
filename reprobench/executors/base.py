from loguru import logger

from reprobench.core.base import Step
from reprobench.executors.events import STORE_RUNSTATS
from reprobench.utils import recv_event

from .db import RunStatistic


class Executor(Step):
    @classmethod
    def register(cls, config={}):
        RunStatistic.create_table()

    @classmethod
    def _handle_event(cls, event_type, payload):
        if event_type == STORE_RUNSTATS:
            RunStatistic.create(**payload)
