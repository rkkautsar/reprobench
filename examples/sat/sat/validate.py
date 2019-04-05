from datetime import datetime
from pathlib import Path

from playhouse.apsw_ext import BooleanField, DateTimeField, ForeignKeyField

from reprobench.core.base import Step, Observer
from reprobench.executors.db import BaseModel, Run
from reprobench.utils import send_event

STORE_SAT_VERDICT = b"satverdict:store"


class SATVerdict(BaseModel):
    created_at = DateTimeField(default=datetime.now)
    run = ForeignKeyField(Run, backref="sat_verdicts", on_delete="cascade")
    is_valid = BooleanField()


class SATObserver(Observer):
    SUBSCRIBED_EVENTS = (STORE_SAT_VERDICT,)

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        if event_type == STORE_SAT_VERDICT:
            SATVerdict.create(**payload)


class SATValidator(Step):
    @classmethod
    def register(cls, config=None):
        SATVerdict.create_table()

    @classmethod
    def execute(cls, context, config=None):
        tool = context["tool"](context)
        task = Path(tool.task).read_text()
        output = tool.get_output().decode()

        satisfiable = "c NOTE: Satisfiable".lower() in task.lower()

        is_valid = (satisfiable and "s SATISFIABLE" in output) or (
            not satisfiable and "s UNSATISFIABLE" in output
        )

        payload = dict(run=context["run"]["id"], is_valid=is_valid)
        send_event(context["socket"], STORE_SAT_VERDICT, payload)
