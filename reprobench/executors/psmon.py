from loguru import logger

try:
    from psmon import ProcessMonitor
    from psmon.limiters import CpuTimeLimiter, MaxMemoryLimiter, WallTimeLimiter
except ImportError:
    logger.warning(
        "You may need to install the `psmon` extra to run with this executor."
    )

from reprobench.utils import send_event

from .base import Executor
from .db import RunStatistic
from .events import STORE_RUNSTATS


class PsmonExecutor(Executor):
    def __init__(self, context, config):
        self.socket = context["socket"]
        self.run_id = context["run"]["id"]

        if config is None:
            config = {}

        wall_grace = config.get("wall_grace", 15)
        self.nonzero_as_rte = config.get("nonzero_rte", True)

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
        elif stats["error"] or (self.nonzero_as_rte and stats["return_code"] != 0):
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
        input_str=None,
        directory=None,
        **kwargs,
    ):
        out_file = open(out_path, "wb")
        err_file = open(err_path, "wb")

        monitor = ProcessMonitor(
            cmdline,
            cwd=directory,
            stdout=out_file,
            stderr=err_file,
            input=input_str,
            freq=15,
        )
        monitor.subscribe("wall_time", WallTimeLimiter(self.wall_limit))
        monitor.subscribe("cpu_time", CpuTimeLimiter(self.cpu_limit))
        monitor.subscribe("max_memory", MaxMemoryLimiter(self.mem_limit))

        logger.debug(f"Running {directory}")
        stats = monitor.run()
        logger.debug(f"Finished {directory}")

        out_file.close()
        err_file.close()

        payload = self.compile_stats(stats)
        send_event(self.socket, STORE_RUNSTATS, payload)

