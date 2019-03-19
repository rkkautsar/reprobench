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
from reprobench.utils import import_class, is_range_str, str_to_range


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


def _bootstrap_parameters(config):
    for (category, parameters) in config["parameters"].items():
        ranged_enum_parameters = {
            key: value
            for key, value in parameters.items()
            if isinstance(parameters[key], list)
        }

        ranged_numbers_parameters = {
            key: str_to_range(value)
            for key, value in parameters.items()
            if isinstance(value, str) and is_range_str(value)
        }

        ranged_parameters = {**ranged_enum_parameters, **ranged_numbers_parameters}

        if len(ranged_parameters) == 0:
            parameter_category = ParameterCategory.create(title=category)
            for (key, value) in parameters.items():
                Parameter.create(category=parameter_category, key=key, value=value)
            return

        constant_parameters = {
            key: value
            for key, value in parameters.items()
            if key not in ranged_parameters
        }
        tuples = [
            [(key, value) for value in values]
            for key, values in ranged_parameters.items()
        ]

        for combination in itertools.product(*tuples):
            category_suffix = ",".join(f"{key}={value}" for key, value in combination)
            parameter_category = ParameterCategory.create(
                title=f"{category}[{category_suffix}]"
            )
            parameters = {**dict(combination), **constant_parameters}
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
    _bootstrap_parameters(config)
    _bootstrap_tasks(config)
    _setup_tools(config)
    _register_steps(config)
    _bootstrap_runs(config, output_dir)
