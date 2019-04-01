from datetime import datetime
from reprobench.core.db import BaseModel, Run
from playhouse.apsw_ext import (
    ForeignKeyField,
    FloatField,
    CharField,
    IntegerField,
    DateTimeField,
)


class RunStatistic(BaseModel):
    TIMEOUT = "TLE"
    MEMOUT = "MEM"
    RUNTIME_ERR = "RTE"
    OUTPUT_LIMIT = "OLE"
    SUCCESS = "OK"

    VERDICT_CHOICES = (
        (TIMEOUT, "Time Limit Exceeded"),
        (MEMOUT, "Memory Limit Exceeded"),
        (RUNTIME_ERR, "Runtime Error"),
        (OUTPUT_LIMIT, "Output Limit Exceeded"),
        (SUCCESS, "Run Successfully"),
    )

    created_at = DateTimeField(default=datetime.now)
    run = ForeignKeyField(
        Run, backref="statistics", on_delete="cascade", primary_key=True
    )
    cpu_time = FloatField(help_text="CPU Time (s)", null=True)
    wall_time = FloatField(help_text="Wall Clock Time (s)", null=True)
    max_memory = FloatField(help_text="Max Memory Usage (KiB)", null=True)
    return_code = IntegerField(help_text="Process Return Code", null=True)
    verdict = CharField(choices=VERDICT_CHOICES, max_length=3, null=True)
