import itertools
from pathlib import Path

import click
from loguru import logger
from tqdm import tqdm

from reprobench.core.db import (
    MODELS,
    Limit,
    Parameter,
    ParameterGroup,
    Run,
    Task,
    TaskGroup,
    Tool,
    ToolParameterGroup,
    db,
)
from reprobench.task_sources.doi import DOISource
from reprobench.task_sources.local import LocalSource
from reprobench.task_sources.url import UrlSource
from reprobench.utils import (
    get_db_path,
    import_class,
    init_db,
    is_range_str,
    read_config,
    str_to_range,
)


def _bootstrap_db(config):
    logger.info("Bootstrapping db...")
    db.connect()
    db.create_tables(MODELS)

    Limit.insert_many(
        [{"type": key, "value": value} for (key, value) in config["limits"].items()]
    ).execute()


def _bootstrap_parameters(config):
    for (group, parameters) in config["parameters"].items():
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
            parameter_group = ParameterGroup.create(name=group)
            for (key, value) in parameters.items():
                Parameter.create(group=parameter_group, key=key, value=value)
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
            combination_str = ",".join(f"{key}={value}" for key, value in combination)
            parameter_group = ParameterGroup.create(name=f"{group}[{combination_str}]")
            parameters = {**dict(combination), **constant_parameters}
            for (key, value) in parameters.items():
                Parameter.create(group=parameter_group, key=key, value=value)


def _bootstrap_tools(config):
    logger.info("Bootstrapping and running setups on tools...")

    Tool.insert_many(
        [
            {
                "name": name,
                "module": tool["module"],
                "version": import_class(tool["module"]).version(),
            }
            for (name, tool) in config["tools"].items()
        ]
    ).execute()

    for tool in config["tools"].values():
        import_class(tool["module"]).setup()
        for prefix in tool["parameters"]:
            for parameter_group in ParameterGroup.select().where(
                ParameterGroup.name.startswith(prefix)
            ):
                if parameter_group.name != prefix and parameter_group.name[-1] != "]":
                    continue
                ToolParameterGroup.create(
                    tool=tool["module"], parameter_group=parameter_group
                )


def _bootstrap_tasks(config):
    logger.info("Bootstrapping tasks...")
    for (group, task) in config["tasks"].items():
        task_group = TaskGroup.create(name=group)

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
            Task.create(group=task_group, path=str(file))


def _register_steps(config):
    logger.info("Registering steps...")
    for step in itertools.chain.from_iterable(config["steps"].values()):
        import_class(step["module"]).register(step.get("config", {}))


def _bootstrap_runs(config, output_dir):
    tools_parameter_groups = ToolParameterGroup.select().iterator()
    tasks = Task.select().iterator()

    for (tool_parameter_group, task) in tqdm(
        itertools.product(tools_parameter_groups, tasks), desc="Bootstrapping runs"
    ):
        directory = (
            Path(output_dir)
            / tool_parameter_group.tool_id
            / tool_parameter_group.parameter_group_id
            / task.group_id
            / Path(task.path).name
        )
        directory.mkdir(parents=True, exist_ok=True)

        Run.create(
            tool=tool_parameter_group.tool_id,
            task=task,
            parameter_group=tool_parameter_group.parameter_group_id,
            directory=directory,
            status=Run.SUBMITTED,
        )


def bootstrap(config, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    db_path = get_db_path(output_dir)
    init_db(db_path)
    _bootstrap_db(config)
    _bootstrap_parameters(config)
    _bootstrap_tools(config)
    _bootstrap_tasks(config)
    _register_steps(config)
    _bootstrap_runs(config, output_dir)


@click.command(name="bootstrap")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    required=True,
    show_default=True,
)
@click.argument("config", type=click.Path())
def cli(config, output_dir):
    config = read_config(config)
    bootstrap(config, output_dir)


if __name__ == "__main__":
    cli()
