import os
import itertools
from loguru import logger
from multiprocessing.pool import ThreadPool
from pathlib import Path
from datetime import datetime
from playhouse.sqliteq import SqliteQueueDatabase
from reprobench.core.bases import Runner
from reprobench.core.db import db, db_bootstrap, Run, Tool, ParameterCategory, Task
from reprobench.utils import import_class


def execute_run(run_id, config):
    # database = SqliteQueueDatabase(db_name, autostart=True)
    # db.initialize(database)
    run = Run.get_by_id(run_id)
    ToolClass = import_class(run.tool.module)
    tool_instance = ToolClass()

    context = config.copy()
    context["tool"] = tool_instance
    context["run"] = run
    logger.info(f"Processing task: {run.directory}")

    for runstep in config["steps"]["run"]:
        Step = import_class(runstep["step"])
        step = Step()
        step.run(context)


class LocalRunner(Runner):
    def __init__(self, config):
        self.config = config
        now = datetime.now()
        self.timestamp = now.strftime("%Y%m%d-%H%M%S")

    def setup(self):
        self.db_name = f"{self.config['title']}_{self.timestamp}.db"
        logger.info(f"Creating Database: {self.db_name}")
        database = SqliteQueueDatabase(self.db_name, autostart=True)
        db.initialize(database)
        db_bootstrap(self.config)

    def create_working_directory(
        self, tool_name, parameter_category, task_category, filename
    ):
        logger.debug(f"{tool_name} {parameter_category} {task_category} {filename}")
        path = (
            Path("./output") / tool_name / parameter_category / task_category / filename
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run(self):
        self.setup()
        queue = []

        for tool_name, tool_module in self.config["tools"].items():
            ToolClass = import_class(tool_module)
            tool_instance = ToolClass()
            tool_instance.setup()

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

                    queue.append((run.id, self.config))
                    # execute_run(run.id, self.config)

            with ThreadPool() as p:
                p.starmap(execute_run, queue)

            tool_instance.teardown()

