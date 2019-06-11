import atexit
import itertools
import json
import shutil
from pathlib import Path

import gevent
from loguru import logger
from peewee import chunked
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
from reprobench.utils import (
    check_valid_config_space,
    get_db_path,
    import_class,
    init_db,
    is_range_str,
    parse_pcs_parameters,
    str_to_range,
)

try:
    from ConfigSpace.read_and_write import pcs
except ImportError:
    pcs = None


def bootstrap_db(output_dir):
    db_path = get_db_path(output_dir)
    init_db(db_path)
    db.connect()
    db.create_tables(MODELS, safe=True)


def bootstrap_limits(config):
    # TODO: handle limit changes
    query = Limit.insert_many(
        [{"key": key, "value": value} for (key, value) in config["limits"].items()]
    ).on_conflict("ignore")
    query.execute()


def bootstrap_steps(config):
    count = Step.select().count()
    new_steps = config["steps"]["run"][count:]
    if len(new_steps) > 0:
        query = Step.insert_many(
            [
                {
                    "category": "run",
                    "module": step["module"],
                    "config": json.dumps(step.get("config", None)),
                }
                for step in new_steps
            ]
        )
        query.execute()


def bootstrap_observers(config, observe_args):
    count = Observer.select().count()
    new_observers = config["observers"][count:]
    if len(new_observers) > 0:
        query = Observer.insert_many(
            [
                {
                    "module": observer["module"],
                    "config": json.dumps(observer.get("config", None)),
                }
                for observer in new_observers
            ]
        )
        query.execute()

        for observer in new_observers:
            observer_class = import_class(observer["module"])
            gevent.spawn(observer_class.observe, *observe_args)


def register_steps(config):
    logger.info("Registering steps...")
    for step in itertools.chain.from_iterable(config["steps"].values()):
        import_class(step["module"]).register(step.get("config", {}))


def bootstrap_tasks(config):
    for (name, tasks) in config["tasks"].items():
        TaskGroup.insert(name=name).on_conflict("ignore").execute()
        with db.atomic():
            for batch in chunked(tasks, 100):
                query = Task.insert_many(
                    [{"path": task, "group": name} for task in batch]
                ).on_conflict("ignore")
                query.execute()


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
        parameter_group = (
            ParameterGroup.insert(name=group, tool=tool).on_conflict("ignore").execute()
        )
        for (key, value) in parameters.items():
            query = Parameter.insert(
                group=parameter_group, key=key, value=value
            ).on_conflict("ignore")
            query.execute()
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
            check_valid_config_space(config_space, parameters)

        combination_str = ",".join(f"{key}={value}" for key, value in combination)
        query = ParameterGroup.insert(
            name=f"{group}[{combination_str}]", tool=tool
        ).on_conflict("ignore")
        parameter_group = query.execute()

        for (key, value) in parameters.items():
            query = Parameter.insert(
                group=parameter_group, key=key, value=value
            ).on_conflict("replace")
            query.execute()


def bootstrap_tools(config):
    logger.info("Bootstrapping tools...")

    for tool_name, tool in config["tools"].items():
        query = Tool.insert(name=tool_name, module=tool["module"]).on_conflict(
            "replace"
        )
        query.execute()

        if "parameters" not in tool:
            create_parameter_group(tool_name, "default", {})
            continue

        for group, parameters in tool["parameters"].items():
            create_parameter_group(tool_name, group, parameters)


def bootstrap_runs(config, output_dir, repeat=1):
    parameter_groups = ParameterGroup.select().iterator()
    tasks = Task.select().iterator()
    total = ParameterGroup.select().count() * Task.select().count()

    with db.atomic():
        for (parameter_group, task) in tqdm(
            itertools.product(parameter_groups, tasks),
            desc="Bootstrapping runs",
            total=total,
        ):
            for iteration in range(repeat):
                directory = (
                    Path(output_dir)
                    / parameter_group.tool_id
                    / parameter_group.name
                    / task.group_id
                    / Path(task.path).name
                    / str(iteration)
                )

                query = Run.insert(
                    id=directory,
                    tool=parameter_group.tool_id,
                    task=task,
                    parameter_group=parameter_group,
                    status=Run.PENDING,
                    iteration=iteration,
                ).on_conflict("ignore")
                query.execute()


def bootstrap(config=None, output_dir=None, repeat=1, observe_args=None):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    bootstrap_db(output_dir)
    bootstrap_limits(config)
    bootstrap_steps(config)
    bootstrap_observers(config, observe_args)
    register_steps(config)
    bootstrap_tasks(config)
    bootstrap_tools(config)
    bootstrap_runs(config, output_dir, repeat)
