import os
import signal
import itertools
import time
import atexit
import subprocess
from string import Template
from tqdm import tqdm
from loguru import logger
from multiprocessing.pool import Pool
from pathlib import Path
from datetime import datetime
from playhouse.apsw_ext import APSWDatabase
from reprobench.core.bases import Runner
from reprobench.core.db import db, db_bootstrap, Run, Tool, ParameterCategory, Task
from reprobench.utils import import_class

DIR = os.path.dirname(os.path.realpath(__file__))


class SlurmRunner(Runner):
    def __init__(
        self,
        config,
        config_path,
        conda_module,
        python_prefix,
        output_dir="./output",
        resume=False,
        teardown=False,
    ):
        self.config = config
        self.config_path = config_path
        self.output_dir = output_dir
        self.conda_module = conda_module
        self.python_prefix = python_prefix
        self.resume = resume
        self.teardown = teardown
        self.queue = []

    def setup(self):
        atexit.register(self.exit)

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

    def exit(self):
        pass

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
            logger.debug("Running setup on all tools...")
            tools = []
            for tool_module in self.config["tools"].values():
                ToolClass = import_class(tool_module)
                tool_instance = ToolClass()
                tool_instance.setup()
                tools.append(tool_instance)
            logger.debug("Generating template")

            slurm_job_path = Path(DIR) / "./slurm.job.tpl"
            with open(slurm_job_path) as tpl:
                template = Template(tpl.read())
                job_str = template.safe_substitute(
                    python_path=self.python_path,
                    conda_module=self.conda_module,
                    config_path=self.config_path,
                    db_path=self.db_path,
                )

            with open(Path(self.output_dir) / "slurm.job", "w") as job:
                job.write(job_str)

            logger.info("Submitting job array to SLURM...")
            subprocess.run(
                ["sbatch", f"--array=1-{len(self.queue)}", slurm_job_path.resolve()]
            )
        else:
            logger.debug("Running teardown on all tools...")
            for tool_module in self.config["tools"].values():
                ToolClass = import_class(tool_module)
                tool_instance = ToolClass()
                tool_instance.teardown()
