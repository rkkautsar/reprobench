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

    tool = ForeignKeyField(Tool, backref="runs", on_delete="cascade")
    parameter_category = ForeignKeyField(
        ParameterCategory, backref="runs", on_delete="cascade"
    )
    task = ForeignKeyField(Task, backref="runs", on_delete="cascade")
    status = IntegerField(choices=STATUS_CHOICES, default=PENDING)
    verdict = CharField(choices=VERDICT_CHOICES, max_length=3, null=True)
    directory = CharField(null=True)
    valid = BooleanField(null=True)
    return_signal = IntegerField(null=True)
    return_code = IntegerField(null=True)

    class Meta:
        only_save_dirty = True


class RunStatistic(BaseModel):
    CPU_TIME = "cpu"
    WALL_TIME = "wall"
    MEM_USAGE = "mem"

    KEY_CHOICES = (
        (CPU_TIME, "CPU Time (s)"),
        (WALL_TIME, "Wall Clock Time (s)"),
        (MEM_USAGE, "Max Memory Usage (KiB)"),
    )

    run = ForeignKeyField(Run, backref="statistics", on_delete="cascade")
    key = CharField(choices=KEY_CHOICES)
    value = CharField()


MODELS = [
    Limit,
    TaskCategory,
    Task,
    ParameterCategory,
    Parameter,
    Run,
    RunStatistic,
    Tool,
]


def db_bootstrap(config):
    db.connect()
    db.create_tables(MODELS)

    Limit.insert_many(
        [{"type": key, "value": value} for (key, value) in config["limits"].items()]
    ).execute()

    Tool.insert_many(
        [{"name": name, "module": module} for (name, module) in config["tools"].items()]
    ).execute()

    for (category, parameters) in config["parameters"].items():
        parameter_category = ParameterCategory.create(title=category)
        for (key, value) in parameters.items():
            Parameter.create(category=parameter_category, key=key, value=value)

    for (category, task) in config["tasks"].items():
        task_category = TaskCategory.create(title=category)
        assert task["type"] == "folder"
        for file in Path().glob(task["path"]):
            Task.create(category=task_category, path=str(file))
