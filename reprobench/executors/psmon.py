import subprocess
from loguru import logger
from pathlib import Path
from psmon import ProcessMonitor
from psmon.limiters import WallTimeLimiter, CpuTimeLimiter, MaxMemoryLimiter

from reprobench.core.bases import Step
from reprobench.core.db import db, Run
from .db import RunStatistic


class PsmonExecutor(Step):
    @classmethod
    def register(cls, config={}):
        RunStatistic.create_table()

    @classmethod
    def execute(cls, context, config={}):
        tool = context["tool"]
        limits = context["limits"]
        tool.pre_run(context)

        cwd = context["run"].directory
        out_file = (Path(cwd) / "run.out").open("wb")
        err_file = (Path(cwd) / "run.err").open("wb")

        with db.atomic("EXCLUSIVE"):
            context["run"].status = Run.RUNNING
            context["run"].save()

        cmd = tool.cmdline(context)
        logger.debug(f"Running {cwd}")
        logger.trace(cmd)

        monitor = ProcessMonitor(
            cmd, cwd=cwd, stdout=out_file, stderr=err_file, freq=15
        )
        monitor.subscribe("wall_time", WallTimeLimiter(limits["time"] + 15))
        monitor.subscribe("cpu_time", CpuTimeLimiter(limits["time"]))
        monitor.subscribe("max_memory", MaxMemoryLimiter(limits["memory"]))

        stats = monitor.run()

        logger.debug(f"Finished {cwd}")
        logger.debug(stats)

        with db.atomic("EXCLUSIVE"):
            context["run"].status = Run.DONE
            context["run"].save()

            verdict = None
            if stats["error"] == TimeoutError:
                verdict = RunStatistic.TIMEOUT
            elif stats["error"] == MemoryError:
                verdict = RunStatistic.MEMOUT
            elif stats["error"] or stats["return_code"] != 0:
                verdict = RunStatistic.RUNTIME_ERR
            else:
                verdict = RunStatistic.SUCCESS

            RunStatistic.create(
                run=context["run"],
                cpu_time=stats["cpu_time"],
                wall_time=stats["wall_time"],
                max_memory=stats["max_memory"],
                return_code=stats["return_code"],
                verdict=verdict,
            )

        tool.post_run(context)

