import subprocess
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
    @classmethod
    def execute(cls, context, config=None):
        tool = context["tool"]
        limits = context["run"]["limits"]
        run_id = context["run"]["id"]
        tool.pre_run(context)

        cwd = context["run"]["directory"]
        out_file = (Path(cwd) / "run.out").open("wb")
        err_file = (Path(cwd) / "run.err").open("wb")

        cmd = tool.cmdline(context)
        logger.debug(f"Running {cwd}")
        logger.trace(cmd)

        monitor = ProcessMonitor(
            cmd, cwd=cwd, stdout=out_file, stderr=err_file, freq=15
        )
        monitor.subscribe("wall_time", WallTimeLimiter(float(limits["time"]) + 15))
        monitor.subscribe("cpu_time", CpuTimeLimiter(float(limits["time"])))
        MB = 1024 * 1024
        monitor.subscribe("max_memory", MaxMemoryLimiter(float(limits["memory"]) * MB))

        send_event(context["socket"], RUN_START, run_id)
        stats = monitor.run()
        send_event(context["socket"], RUN_FINISH, run_id)

        logger.debug(f"Finished {cwd}")

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

        payload = dict(run_id=run_id, verdict=verdict, **stats)
        send_event(context["socket"], STORE_RUNSTATS, payload)

        tool.post_run(context)
