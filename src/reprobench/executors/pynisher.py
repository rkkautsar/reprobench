import logging
import pynisher
import subprocess
from pathlib import Path

from reprobench.core.bases import Step
from reprobench.core.db import Run, RunStatistic

log = logging.getLogger(__name__)


class PynisherExecutor(Step):
    def run(self, context):
        tool = context["tool"]
        limits = context["limits"]
        tool.pre_run(context)

        cwd = context["working_directory"]
        out_file = (Path(cwd) / "run.out").open("wb")
        err_file = (Path(cwd) / "run.err").open("wb")

        context["run"].status = Run.RUNNING
        context["run"].save()

        def run_tool():
            subprocess.run(
                tool.cmdline(context), cwd=cwd, stdout=out_file, stderr=err_file
            )

        fun = pynisher.enforce_limits(
            cpu_time_in_s=limits["time"], mem_in_mb=limits["memory"]
        )(run_tool)

        fun()

        log.debug(fun)

        context["run"].status = Run.DONE
        context["run"].verdict = Run.SUCCESS
        context["run"].save()

        tool.post_run(context)

        RunStatistic.create(
            run=context["run"], key=RunStatistic.WALL_TIME, value=fun.wall_clock_time
        )
        RunStatistic.create(
            run=context["run"],
            key=RunStatistic.CPU_TIME,
            value=fun.resources_function[0],
        )  # utime
        RunStatistic.create(
            run=context["run"],
            key=RunStatistic.MEM_USAGE,
            value=fun.resources_function[2],
        )  # maxrss

