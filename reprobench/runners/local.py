import os
import signal
import itertools
import time
from loguru import logger
from multiprocessing.pool import ThreadPool
from pathlib import Path
from datetime import datetime
from playhouse.sqliteq import SqliteQueueDatabase
from reprobench.core.bases import Runner
from reprobench.core.db import db, db_bootstrap, Run, Tool, ParameterCategory, Task
from reprobench.utils import import_class


class LocalRunner(Runner):
    def __init__(self, config, output_dir="./output", resume=False):
        self.config = config
        self.output_dir = output_dir
        self.resume = resume
        self.queue = []

    def execute_run(self, run_id):
        run = Run.get_by_id(run_id)
        ToolClass = import_class(run.tool.module)
        tool_instance = ToolClass()

        context = self.config.copy()
        context["tool"] = tool_instance
        context["run"] = run
        logger.info(f"Processing task: {run.directory}")

        for runstep in self.config["steps"]["run"]:
            Step = import_class(runstep["step"])
            step = Step()
            step.run(context)

    def setup(self):
        signal.signal(signal.SIGTERM, self.exit)
        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)

        self.db_path = Path(self.output_dir) / f"{self.config['title']}.benchmark.db"
        db_created = Path(self.db_path).is_file()

        if db_created and not self.resume:
            logger.error(
                "It seems that a previous runs exist at the output directory. Please use --resume to resume runs."
            )
            exit(1)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Creating Database: {self.db_path}")
        self.database = SqliteQueueDatabase(self.db_path, autostart=True)
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

    def exit(self, *args):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        logger.warning("it is not guaranteed that all processes will be terminated!")
        logger.info("Sending SIGTERM...")
        os.killpg(os.getpgid(0), signal.SIGTERM)
        logger.info("Sleeping for 3s...")
        time.sleep(3)
        logger.warning("Sending SIGKILL...")
        os.killpg(os.getpgid(0), signal.SIGKILL)

    def populate_unfinished_runs(self):
        query = Run.select(Run.id).where(Run.status < Run.DONE)
        self.queue = [run.id for run in query]

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
                        status=Run.SUBMITTED,
                    )

                    self.queue.append(run.id)

    def run(self):
        self.setup()

        if self.resume:
            logger.info("Resuming unfinished runs...")
            self.populate_unfinished_runs()

        if len(self.queue) == 0:
            logger.success("No tasks remaining to run")
            exit(0)

        logger.debug("Running setup on all tools...")
        tools = []
        for tool_module in self.config["tools"].values():
            ToolClass = import_class(tool_module)
            tool_instance = ToolClass()
            tool_instance.setup()
            tools.append(tool_instance)

        logger.debug("Executing runs...")
        with ThreadPool() as p:
            p.map(self.execute_run, self.queue)

        logger.debug("Running teardown on all tools...")
        for tool in tools:
            tool.teardown()

        self.database.stop()

