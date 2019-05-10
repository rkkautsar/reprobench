import atexit
import itertools
import json
import shutil
from pathlib import Path

from loguru import logger
from tqdm import tqdm

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
from reprobench.utils import get_db_path, import_class, init_db, parse_pcs_parameters

try:
    from ConfigSpace.read_and_write import pcs
except ImportError:
    pcs = None


def bootstrap_db(output_dir):
    db_path = get_db_path(output_dir)
    init_db(db_path)
    db.connect()
    db.create_tables(MODELS)


def bootstrap_limits(config):
    Limit.insert_many(
        [{"key": key, "value": value} for (key, value) in config["limits"].items()]
    ).execute()


def bootstrap_steps(config):
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


def bootstrap_observers(config):
    Observer.insert_many(
        [
            {
                "module": observer["module"],
                "config": json.dumps(observer.get("config", None)),
            }
            for observer in config["observers"]
        ]
    ).execute()


def register_steps(config):
    logger.info("Registering steps...")
    for step in itertools.chain.from_iterable(config["steps"].values()):
        import_class(step["module"]).register(step.get("config", {}))


def bootstrap_tasks(config):
    for (name, tasks) in config["tasks"].items():
        task_group = TaskGroup.create(name=name)
        Task.insert_many([{"path": task, "group": name} for task in tasks]).execute()


def create_parameter_group(tool, group, parameters):
    PCS_KEY = "__pcs"
    pcs_parameters = {}
    use_pcs = PCS_KEY in parameters
    config_space = None

    if use_pcs:
        pcs_text = parameters.pop(PCS_KEY)
        lines = pcs_text.split("\n")
        config_space = pcs.read(lines)
        pcs_parameters = parse_pcs_parameters(lines)

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

    ranged_parameters = {
        **pcs_parameters,
        **ranged_enum_parameters,
        **ranged_numbers_parameters,
    }

    if len(ranged_parameters) == 0:
        parameter_group = ParameterGroup.create(name=group, tool=tool)
        for (key, value) in parameters.items():
            Parameter.create(group=parameter_group, key=key, value=value)
        return

    constant_parameters = {
        key: value for key, value in parameters.items() if key not in ranged_parameters
    }

    tuples = [
        [(key, value) for value in values] for key, values in ranged_parameters.items()
    ]

    for combination in itertools.product(*tuples):
        parameters = {**dict(combination), **constant_parameters}

        if use_pcs:
            _check_valid_config_space(config_space, parameters)

        combination_str = ",".join(f"{key}={value}" for key, value in combination)
        parameter_group = ParameterGroup.create(
            name=f"{group}[{combination_str}]", tool=tool
        )

        for (key, value) in parameters.items():
            Parameter.create(group=parameter_group, key=key, value=value)


def bootstrap_tools(config):
    logger.info("Bootstrapping tools...")

    for tool_name, tool in config["tools"].items():
        Tool.create(name=tool_name, module=tool["module"], version=tool["version"])

        if "parameters" not in tool:
            create_parameter_group(tool["module"], "default", {})
            continue

        for group, parameters in tool["parameters"].items():
            create_parameter_group(tool["module"], group, parameters)


def bootstrap_runs(config, output_dir, repeat=1):
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

    bootstrap_db(output_dir)
    bootstrap_limits(config)
    bootstrap_steps(config)
    bootstrap_observers(config)
    register_steps(config)
    bootstrap_tasks(config)
    bootstrap_tools(config)
    bootstrap_runs(config, output_dir, repeat)

    atexit.unregister(shutil.rmtree)
