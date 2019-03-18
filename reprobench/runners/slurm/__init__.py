import os
import signal
import itertools
import time
import subprocess
from string import Template
from loguru import logger
from multiprocessing.pool import Pool
from pathlib import Path
from playhouse.apsw_ext import APSWDatabase
from reprobench.core.bases import Runner
from reprobench.core.db import db, db_bootstrap, Run, Tool, ParameterCategory, Task
from reprobench.utils import import_class

from .utils import create_ranges

DIR = os.path.dirname(os.path.realpath(__file__))


class SlurmRunner(Runner):
    def __init__(
        self, config, config_path, python_path, output_dir="./output", **kwargs
    ):
        self.config = config
        self.config_path = config_path
        self.output_dir = output_dir
        self.python_path = python_path
        self.resume = kwargs.get("resume", False)
        self.teardown = kwargs.get("teardown", False)
        self.run_template_file = kwargs.get("run_template_file")
        self.compile_template_file = kwargs.get("compile_template_file")
        self.queue = []

        if self.run_template_file is None:
            self.run_template_file = os.path.join(DIR, "./slurm.run.job.tpl")
        if self.compile_template_file is None:
            self.compile_template_file = (os.path.join(DIR, "./slurm.compile.job.tpl"),)

    def setup(self):
        self.db_path = Path(self.output_dir) / f"{self.config['title']}.benchmark.db"
        db_created = Path(self.db_path).is_file()

        if db_created and not self.resume:
            logger.error(
                "It seems that a previous runs exist at the output directory. Please use --resume to resume runs."
            )
            exit(1)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Creating Database: {self.db_path}")
        self.database = APSWDatabase(str(self.db_path))
        db.initialize(self.database)

        if not db_created:
            logger.info("Bootstrapping db...")
            db_bootstrap(self.config)
            logger.info("Initializing runs...")
            self.init_runs()

        logger.info("Registering steps...")
        for runstep in itertools.chain.from_iterable(self.config["steps"].values()):
            Step = import_class(runstep["step"])
            Step.register(runstep.get("config", {}))

    def create_working_directory(
        self, tool_name, parameter_category, task_category, filename
    ):
        path = (
            Path(self.output_dir)
            / tool_name
            / parameter_category
            / task_category
            / filename
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def populate_unfinished_runs(self):
        query = Run.select(Run.id).where(Run.status < Run.DONE)
        self.queue = [(run.id, self.config, self.db_path) for run in query]

    def init_runs(self):
        for tool_name, tool_module in self.config["tools"].items():
            for (parameter_category_name, (task_category, task)) in itertools.product(
                self.config["parameters"], self.config["tasks"].items()
            ):
                # only folder task type for now
                assert task["type"] == "folder"

                files = Path().glob(task["path"])
                for file in files:
                    context = self.config.copy()
                    directory = self.create_working_directory(
                        tool_name, parameter_category_name, task_category, file.name
                    )

                    tool = Tool.get(Tool.module == tool_module)
                    parameter_category = ParameterCategory.get(
                        ParameterCategory.title == parameter_category_name
                    )
                    task = Task.get(Task.path == str(file))

                    run = Run.create(
                        tool=tool,
                        task=task,
                        parameter_category=parameter_category,
                        directory=directory,
                    )

                    self.queue.append(run.id)

    def run(self):
        if not self.teardown:
            self.setup()

            if self.resume:
                logger.info("Resuming unfinished runs...")
                self.populate_unfinished_runs()

            logger.debug("Running setup on all tools...")
            tools = []
            for tool_module in self.config["tools"].values():
                ToolClass = import_class(tool_module)
                tool_instance = ToolClass()
                tool_instance.setup()
                tools.append(tool_instance)
            logger.debug("Generating template")

            with open(self.run_template_file) as tpl:
                template = Template(tpl.read())
                job_str = template.safe_substitute(
                    mem=int(1 + self.config["limits"]["memory"] / 1024 / 1024),  # mb
                    time=int(1 + (self.config["limits"]["time"] + 15) / 60),  # minutes
                    run_ids=create_ranges(self.queue),
                    python_path=self.python_path,
                    config_path=self.config_path,
                    db_path=self.db_path,
                )

            slurm_job_path = Path(self.output_dir) / "slurm.job"
            with open(slurm_job_path, "w") as job:
                job.write(job_str)

            logger.info("Submitting job array to SLURM...")
            sbatch_cmd = ["sbatch", str(slurm_job_path.resolve())]
            logger.debug(" ".join(sbatch_cmd))
            subprocess.run(sbatch_cmd)
        else:
            logger.debug("Running teardown on all tools...")
            for tool_module in self.config["tools"].values():
                ToolClass = import_class(tool_module)
                tool_instance = ToolClass()
                tool_instance.teardown()
