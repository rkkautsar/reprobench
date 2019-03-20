from pathlib import Path
from datetime import datetime
from peewee import Proxy, Model
from playhouse.apsw_ext import (
    DateTimeField,
    CharField,
    ForeignKeyField,
    IntegerField,
    BooleanField,
    CompositeKey,
    FloatField,
)

db = Proxy()


class BaseModel(Model):
    class Meta:
        database = db


class Limit(BaseModel):
    type = CharField(max_length=32, primary_key=True)
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
    name = CharField(primary_key=True)


class Parameter(BaseModel):
    group = ForeignKeyField(ParameterGroup, backref="parameters")
    key = CharField()
    value = CharField()

    class Meta:
        primary_key = CompositeKey("group", "key")


class ToolParameterGroup(BaseModel):
    tool = ForeignKeyField(Tool)
    parameter_group = ForeignKeyField(ParameterGroup)

    class Meta:
        primary_key = CompositeKey("tool", "parameter_group")


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
    parameter_group = ForeignKeyField(ParameterGroup, backref="runs")
    task = ForeignKeyField(Task, backref="runs")
    status = IntegerField(choices=STATUS_CHOICES, default=PENDING)
    directory = CharField(null=True)

    class Meta:
        only_save_dirty = True


MODELS = (
    Limit,
    TaskGroup,
    Task,
    Tool,
    ParameterGroup,
    Parameter,
    Run,
    ToolParameterGroup,
)
