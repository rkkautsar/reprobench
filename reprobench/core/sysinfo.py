import platform

from playhouse.apsw_ext import CharField, FloatField, ForeignKeyField, IntegerField

from reprobench.core.base import Step, Observer
from reprobench.core.db import BaseModel, Run, db
from reprobench.utils import send_event

try:
    import psutil
    from cpuinfo import get_cpu_info
except ImportError:
    psutil = None
    get_cpu_info = None


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
STORE_SYSINFO = b"sysinfo:store"


class SystemInfoObserver(Observer):
    SUBSCRIBED_EVENTS = (STORE_SYSINFO,)

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        if event_type == STORE_SYSINFO:
            node = payload["node"]
            run = payload["run_id"]

            Node.insert(**node).on_conflict("ignore").execute()
            RunNode.insert(run=run, node=node["hostname"]).on_conflict(
                "replace"
            ).execute()


class CollectSystemInfo(Step):
    @classmethod
    def register(cls, config=None):
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
    def execute(cls, context, config=None):
        hostname = platform.node()
        info = cls._get_system_info()
        run_id = context["run"]["id"]
        payload = dict(run_id=run_id, node=dict(hostname=hostname, **info))
        send_event(context["socket"], STORE_SYSINFO, payload)
