import itertools
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from reprobench.core.db import (
    MODELS,
    Limit,
    Parameter,
    ParameterCategory,
    Run,
    Task,
    TaskCategory,
    Tool,
    db,
)
from reprobench.task_sources.doi import DOISource
from reprobench.task_sources.local import LocalSource
from reprobench.task_sources.url import UrlSource
from reprobench.utils import import_class


def _bootstrap_db(config):
    logger.info("Bootstrapping db...")
    db.connect()
    db.create_tables(MODELS)

    Limit.insert_many(
        [{"type": key, "value": value} for (key, value) in config["limits"].items()]
    ).execute()

    Tool.insert_many(
        [{"name": name, "module": module} for (name, module) in config["tools"].items()]
    ).execute()

    for (category, parameters) in config["parameters"].items():
        parameter_category = ParameterCategory.create(title=category)
        for (key, value) in parameters.items():
            Parameter.create(category=parameter_category, key=key, value=value)


def _bootstrap_tasks(config):
    logger.info("Bootstrapping tasks...")
    for (category, task) in config["tasks"].items():
        task_category = TaskCategory.create(title=category)

        source = None
        if task["type"] == "local":
            source = LocalSource(**task)
        elif task["type"] == "url":
            source = UrlSource(**task)
        elif task["type"] == "doi":
            source = DOISource(**task)
        else:
            raise NotImplementedError(
                f"No implementation for task source {task['type']}"
            )

        files = source.setup()
        for file in files:
            Task.create(category=task_category, path=str(file))


def _setup_tools(config):
    logger.info("Running setups on tools...")
    for tool in config["tools"].values():
        import_class(tool).setup()


def _register_steps(config):
    logger.info("Registering steps...")
    for runstep in itertools.chain.from_iterable(config["steps"].values()):
        import_class(runstep["step"]).register(runstep.get("config", {}))


def _bootstrap_runs(config, output_dir):
    tools = Tool.select(Tool.id, Tool.name).iterator()
    parameters = ParameterCategory.select(
        ParameterCategory.id, ParameterCategory.title
    ).iterator()
    tasks = (
        Task.select(Task.id, Task.path, TaskCategory.title)
        .join(TaskCategory)
        .iterator()
    )

    for (tool, parameter, task) in tqdm(
        itertools.product(tools, parameters, tasks), desc="Bootstrapping runs"
    ):
        directory = (
            Path(output_dir)
            / tool.name
            / parameter.title
            / task.category.title
            / Path(task.path).name
        )
        directory.mkdir(parents=True, exist_ok=True)

        Run.create(
            tool=tool,
            task=task,
            parameter_category=parameter,
            directory=directory,
            status=Run.SUBMITTED,
        )


def bootstrap(config, output_dir):
    _bootstrap_db(config)
    _bootstrap_tasks(config)
    _setup_tools(config)
    _register_steps(config)
    _bootstrap_runs(config, output_dir)
