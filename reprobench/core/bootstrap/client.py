from loguru import logger

from reprobench.task_sources.doi import DOISource
from reprobench.task_sources.file import FileSource
from reprobench.task_sources.url import UrlSource
from reprobench.utils import import_class


def bootstrap_tasks(config):
    logger.info("Bootstrapping tasks...")
    available_sources = (FileSource, UrlSource, DOISource)

    logger.trace(config)

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

        tasks = source.setup()
        task_groups[group] = [str(task) for task in tasks]

    return task_groups


def bootstrap_tools(config):
    logger.info("Setting up tools...")

    tools = {}
    for tool_name, tool in config["tools"].items():
        tools[tool_name] = dict(
            module=tool["module"], parameters=tool.get("parameters")
        )

    return tools


def bootstrap(config):
    tasks = bootstrap_tasks(config)
    tools = bootstrap_tools(config)

    return dict(tasks=tasks, tools=tools)
