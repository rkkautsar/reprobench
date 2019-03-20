import psutil
import platform

from loguru import logger
from playhouse.apsw_ext import CharField, FloatField, ForeignKeyField, IntegerField
from cpuinfo import get_cpu_info

from reprobench.core.bases import Step
from reprobench.core.db import db, BaseModel, Run


class Node(BaseModel):
    hostname = CharField(primary_key=True)
    platform = CharField(null=True)
    arch = CharField(null=True)
    python = CharField(null=True)
    cpu = CharField(null=True)
    cpu_count = IntegerField(null=True)
    cpu_min_freq = FloatField(null=True)
    cpu_max_freq = FloatField(null=True)
    mem_total = IntegerField(null=True)
    mem_available = IntegerField(null=True)
    swap_total = IntegerField(null=True)
    swap_available = IntegerField(null=True)


class RunNode(BaseModel):
    run = ForeignKeyField(Run, backref="run_node", primary_key=True)
    node = ForeignKeyField(Node, backref="runs")


MODELS = (Node, RunNode)


class CollectSystemInfo(Step):
    @classmethod
    def register(cls, config={}):
        db.create_tables(MODELS)

    @classmethod
    def _get_system_info(cls):
        cpu_info = get_cpu_info()
        cpu_freq = psutil.cpu_freq()
        mem_info = psutil.virtual_memory()
        swap_info = psutil.swap_memory()

        info = {}
        info["platform"] = platform.platform(aliased=True)
        info["arch"] = cpu_info["arch"]
        info["python"] = cpu_info["python_version"]
        info["cpu"] = cpu_info["brand"]
        info["cpu_count"] = psutil.cpu_count()
        info["cpu_min_freq"] = cpu_freq.min
        info["cpu_max_freq"] = cpu_freq.max
        info["mem_total"] = mem_info.total
        info["mem_available"] = mem_info.available
        info["swap_total"] = swap_info.total
        info["swap_available"] = swap_info.free

        return info

    @classmethod
    def execute(cls, context, config={}):
        hostname = platform.node()

        with db.atomic("EXCLUSIVE"):
            is_exist = Node.select(Node.hostname == hostname).count() > 0
            if not is_exist:
                info = cls._get_system_info()
                Node.create(hostname=hostname, **info)

            RunNode.replace(run=context["run"], node=hostname)
