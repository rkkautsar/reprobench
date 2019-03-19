from pathlib import Path
from datetime import datetime
from peewee import Proxy, Model
from playhouse.apsw_ext import (
    DateTimeField,
    CharField,
    ForeignKeyField,
    IntegerField,
    BooleanField,
)

db = Proxy()


class BaseModel(Model):
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db


class Limit(BaseModel):
    type = CharField(max_length=32, unique=True)
    value = CharField()


class TaskCategory(BaseModel):
    title = CharField()


class Task(BaseModel):
    category = ForeignKeyField(TaskCategory, backref="tasks", on_delete="cascade")
    path = CharField()


class Tool(BaseModel):
    module = CharField(unique=True)
    name = CharField()
    version = CharField(null=True)


class ParameterCategory(BaseModel):
    title = CharField()


class Parameter(BaseModel):
    category = ForeignKeyField(
        ParameterCategory, backref="parameters", on_delete="cascade"
    )
    key = CharField()
    value = CharField()

    class Meta:
        indexes = ((("category", "key"), True),)


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

    tool = ForeignKeyField(Tool, backref="runs", on_delete="cascade")
    parameter_category = ForeignKeyField(
        ParameterCategory, backref="runs", on_delete="cascade"
    )
    task = ForeignKeyField(Task, backref="runs", on_delete="cascade")
    status = IntegerField(choices=STATUS_CHOICES, default=PENDING)
    directory = CharField(null=True)

    class Meta:
        only_save_dirty = True


MODELS = [Limit, TaskCategory, Task, ParameterCategory, Parameter, Run, Tool]

