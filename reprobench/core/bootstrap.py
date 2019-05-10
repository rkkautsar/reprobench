import atexit
import itertools
import json
import re
import shutil
from ast import literal_eval
from collections.abc import Iterable
from pathlib import Path

import click
import numpy
import zmq
from loguru import logger
from tqdm import tqdm

from reprobench.console.decorators import common, server_info
from reprobench.core.db import (
    MODELS,
    Limit,
    Observer,
    Parameter,
    ParameterGroup,
    Run,
    Step,
    Task,
    TaskGroup,
    Tool,
    db,
)
from reprobench.core.events import BOOTSTRAP
from reprobench.core.exceptions import NotSupportedError
from reprobench.task_sources.doi import DOISource
from reprobench.task_sources.local import LocalSource
from reprobench.task_sources.url import UrlSource
from reprobench.utils import (
    get_db_path,
    import_class,
    init_db,
    is_range_str,
    read_config,
    send_event,
    str_to_range,
)

try:
    from ConfigSpace.read_and_write import pcs
except ImportError:
    pcs = None


def _bootstrap_db(config):
    logger.info("Bootstrapping db...")
    db.connect()
    db.create_tables(MODELS)

    Limit.insert_many(
        [{"key": key, "value": value} for (key, value) in config["limits"].items()]
    ).execute()

    Step.insert_many(
        [
            {
                "category": key,
                "module": step["module"],
                "config": json.dumps(step.get("config", None)),
            }
            for key, steps in config["steps"].items()
            for step in steps
        ]
    ).execute()

    Observer.insert_many(
        [
            {
                "module": observer["module"],
                "config": json.dumps(observer.get("config", None)),
            }
            for observer in config["observers"]
        ]
    ).execute()

def _bootstrap_tools(config):
    logger.info("Bootstrapping and running setups on tools...")

    for tool_name, tool in config["tools"].items():
        tool_module = import_class(tool["module"])

        if not tool_module.is_ready():
            tool_module.setup()

        version = import_class(tool["module"]).version()

        Tool.create(name=tool_name, module=tool["module"], version=version)

        if "parameters" not in tool:
            _create_parameter_group(tool["module"], "default", {})
            continue

        for group, parameters in tool["parameters"].items():
            _create_parameter_group(tool["module"], group, parameters)


def _bootstrap_tasks(config):
    logger.info("Bootstrapping tasks...")
    for (group, task) in config["tasks"].items():
        task_group = TaskGroup.create(name=group)

        source = None

        # @TODO use chain of command
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


def _bootstrap_runs(config, output_dir, repeat=1):
    parameter_groups = ParameterGroup.select().iterator()
    tasks = Task.select().iterator()
    total = ParameterGroup.select().count() * Task.select().count()

    for (parameter_group, task) in tqdm(
        itertools.product(parameter_groups, tasks),
        desc="Bootstrapping runs",
        total=total,
    ):
        directory = (
            Path(output_dir)
            / parameter_group.tool_id
            / parameter_group.name
            / task.group_id
            / Path(task.path).name
        )

        with db.atomic():
            for _ in range(repeat):
                Run.create(
                    tool=parameter_group.tool_id,
                    task=task,
                    parameter_group=parameter_group,
                    directory=directory,
                    status=Run.PENDING,
                )


def bootstrap(config=None, output_dir=None, repeat=1):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    atexit.register(shutil.rmtree, output_dir)
    db_path = get_db_path(output_dir)
    init_db(db_path)
    _bootstrap_db(config)
    _bootstrap_tools(config)
    _bootstrap_tasks(config)
    _register_steps(config)
    _bootstrap_runs(config, output_dir, repeat)
    atexit.unregister(shutil.rmtree)


@click.command(name="bootstrap")
@click.option("-r", "--repeat", type=int, default=1)
@click.option(
    "-d",
    "--output-dir",
    type=click.Path(),
    default="./output",
    required=True,
    show_default=True,
)
@click.argument("config", type=click.Path(), default="./benchmark.yml")
@server_info
@common
def cli(server_address, config, output_dir, **kwargs):
    config = read_config(config, resolve_files=True)
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(server_address)
    payload = dict(config=config, output_dir=output_dir, **kwargs)
    send_event(socket, BOOTSTRAP, payload)


if __name__ == "__main__":
    cli()
