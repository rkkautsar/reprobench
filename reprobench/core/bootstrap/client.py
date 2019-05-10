from loguru import logger

from reprobench.core.exceptions import NotSupportedError
from reprobench.task_sources.doi import DOISource
from reprobench.task_sources.local import LocalSource
from reprobench.task_sources.url import UrlSource
from reprobench.utils import import_class


def bootstrap_tasks(config):
    logger.info("Bootstrapping tasks...")
    available_sources = (LocalSource, UrlSource, DOISource)

    task_groups = {}
    for (group, task) in config["tasks"].items():
        logger.trace(f"Processing task group: {group}")

        for TaskSource in available_sources:
            if task["type"] == TaskSource.TYPE:
                source = TaskSource(**task)
                break
        else:
            raise NotImplementedError(
                f"No implementation for task source {task['type']}"
            )

        task_groups[group] = [str(task) for task in source.setup()]

    return task_groups


def bootstrap_tools(config):
    logger.info("Setting up tools...")

    tools = {}
    for tool_name, tool in config["tools"].items():
        tool_module = import_class(tool["module"])

        if not tool_module.is_ready():
            tool_module.setup()

        version = import_class(tool["module"]).version()
        tools[tool_name] = dict(
            module=tool["module"], version=version, parameters=tool.get("parameters")
        )

    return tools


def bootstrap(config):
    tasks = bootstrap_tasks(config)
    tools = bootstrap_tools(config)

    return dict(tasks=tasks, tools=tools)
