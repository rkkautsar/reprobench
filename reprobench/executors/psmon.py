from pathlib import Path

from loguru import logger
from psmon import ProcessMonitor
from psmon.limiters import CpuTimeLimiter, MaxMemoryLimiter, WallTimeLimiter

from reprobench.core.events import RUN_FINISH, RUN_START
from reprobench.utils import send_event

from .base import Executor
from .db import RunStatistic
from .events import STORE_RUNSTATS


class PsmonExecutor(Executor):
    def __init__(self, context, config):
        self.socket = context["socket"]
        self.run_id = context["run"]["id"]

        if config is not None:
            wall_grace = config.get("wall_grace")
        else:
            wall_grace = 15

        limits = context["run"]["limits"]
        time_limit = float(limits["time"])
        MB = 1024 * 1024

        self.wall_limit = time_limit + wall_grace
        self.cpu_limit = time_limit
        self.mem_limit = float(limits["memory"]) * MB

    def compile_stats(self, stats):
        verdict = None
        if stats["error"] == TimeoutError:
            verdict = RunStatistic.TIMEOUT
        elif stats["error"] == MemoryError:
            verdict = RunStatistic.MEMOUT
        elif stats["error"] or stats["return_code"] != 0:
            verdict = RunStatistic.RUNTIME_ERR
        else:
            verdict = RunStatistic.SUCCESS

        del stats["error"]

        return dict(run_id=self.run_id, verdict=verdict, **stats)

    def run(
        self,
        cmdline,
        out_path=None,
        err_path=None,
        input=None,
        directory=None,
        **kwargs,
    ):
        out_file = open(out_path, "wb")
        err_file = open(out_path, "wb")

        monitor = ProcessMonitor(
            cmdline,
            cwd=directory,
            stdout=out_file,
            stderr=err_file,
            input=input,
            freq=15,
        )
        monitor.subscribe("wall_time", WallTimeLimiter(self.wall_limit))
        monitor.subscribe("cpu_time", CpuTimeLimiter(self.cpu_limit))
        monitor.subscribe("max_memory", MaxMemoryLimiter(self.mem_limit))

        logger.debug(f"Running {directory}")
        send_event(self.socket, RUN_START, self.run_id)
        stats = monitor.run()
        send_event(self.socket, RUN_FINISH, self.run_id)
        logger.debug(f"Finished {directory}")

        out_file.close()
        err_file.close()

        payload = self.compile_stats(stats)
        send_event(self.socket, STORE_RUNSTATS, payload)

