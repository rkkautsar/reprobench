"""
TODO: Update to latest refactor
"""

import subprocess
import functools
import operator
from pathlib import Path

from reprobench.core.bases import Step
from reprobench.core.db import Run, RunStatistic
from reprobench.utils import find_executable, silent_run


class RunsolverExecutor(Step):
    def __init__(self):
        self.executable = find_executable("runsolver")

    def run(self, context):
        tool = context["tool"]
        limits = context["limits"]
        tool.pre_run(context)

        cwd = context["working_directory"]
        out_file = (Path(cwd) / "run.out").open("wb")
        err_file = (Path(cwd) / "run.err").open("wb")

        context["run"].status = Run.RUNNING
        context["run"].save()

        process = subprocess.run(
            [
                self.executable,
                "-w",
                "run.watcher",
                "-v",
                "run.stat",
                "--cores",
                limits["cores"],
                "-C",
                str(limits["time"]),
                "--vsize-limit",
                str(limits["memory"]),
                # "-O", "0,{}".format(limits["output"]),
                "--",
            ]
            + tool.cmdline(context),
            cwd=cwd,
            stdout=out_file,
            stderr=err_file,
        )

        context["run"].status = Run.DONE
        context["run"].verdict = Run.SUCCESS
        context["run"].save()

        tool.post_run(context)

        out_file.close()
        err_file.close()

        stat_file = Path(cwd) / "run.stat"

        stat_map = {
            "WCTIME": RunStatistic.WALL_TIME,
            "CPUTIME": RunStatistic.CPU_TIME,
            "MAXVM": RunStatistic.MEM_USAGE,
        }

        with stat_file.open() as f:
            for line in f:
                if line.startswith("#"):
                    continue
                key, value = line.split("=")
                if key in stat_map:
                    RunStatistic.create(
                        run=context["run"], key=stat_map[key], value=value
                    )
                elif key == "TIMEOUT" and value == "true":
                    context["run"].verdict = Run.TIMEOUT
                    context["run"].save()
                elif key == "MEMOUT" and value == "true":
                    context["run"].verdict = Run.MEMOUT
                    context["run"].save()
