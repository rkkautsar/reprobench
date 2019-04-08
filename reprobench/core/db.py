from datetime import datetime

from playhouse.apsw_ext import (
    Model,
    Proxy,
    CharField,
    CompositeKey,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    TextField,
)

db = Proxy()


class BaseModel(Model):
    class Meta:
        database = db


class Limit(BaseModel):
    key = CharField(max_length=32, primary_key=True)
    value = CharField()


class TaskGroup(BaseModel):
    name = CharField(primary_key=True)


class Task(BaseModel):
    group = ForeignKeyField(TaskGroup, backref="tasks")
    path = CharField(primary_key=True)


class Tool(BaseModel):
    module = CharField(primary_key=True)
    name = CharField()
    version = CharField(null=True)


class ParameterGroup(BaseModel):
    name = CharField()
    tool = ForeignKeyField(Tool, backref="parameter_groups")

    class Meta:
        indexes = ((("name", "tool"), True),)


class Parameter(BaseModel):
    group = ForeignKeyField(ParameterGroup, backref="parameters")
    key = CharField()
    value = CharField()

    class Meta:
        primary_key = CompositeKey("group", "key")


class BasePlugin(BaseModel):
    module = CharField(index=True)
    config = TextField()


class Step(BasePlugin):
    RUN = "run"
    ANALYSIS = "analysis"

    CATEGORY_CHOICES = ((RUN, "Single run step"), (ANALYSIS, "Analysis step"))

    category = CharField(choices=CATEGORY_CHOICES, index=True)


class Observer(BasePlugin):
    pass


class Run(BaseModel):
    FAILED = -2
    CANCELED = -1
    PENDING = 0
    SUBMITTED = 1
    RUNNING = 2
    DONE = 3

    STATUS_CHOICES = (
        (FAILED, "Failed"),
        (CANCELED, "Canceled"),
        (PENDING, "Pending"),
        (SUBMITTED, "Submitted"),
        (RUNNING, "Running"),
        (DONE, "Done"),
    )

    created_at = DateTimeField(default=datetime.now)
    tool = ForeignKeyField(Tool, backref="runs")
    tool_version = CharField(null=True)
    parameter_group = ForeignKeyField(ParameterGroup, backref="runs")
    task = ForeignKeyField(Task, backref="runs")
    status = IntegerField(choices=STATUS_CHOICES, default=PENDING)
    directory = CharField(null=True)
    last_step = ForeignKeyField(Step, null=True)


MODELS = (Limit, TaskGroup, Task, Tool, ParameterGroup, Parameter, Run, Step, Observer)
