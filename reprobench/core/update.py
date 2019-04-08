import json

from reprobench.core.db import Step
from reprobench.utils import get_db_path, init_db, import_class


def _update_step(category, steps):
    current_step_count = Step.select().where(Step.category == category).count()
    for step in steps[current_step_count:]:
        import_class(step["module"]).register(step.get("config", {}))
        Step.create(
            category=category,
            module=step["module"],
            config=json.dumps(step.get("config", None)),
        )


def update_steps(config):
    step_categories = ((Step.RUN, "run"), (Step.ANALYSIS, "analysis"))

    for category, key in step_categories:
        _update_step(category, config["steps"][key])


def update(config=None, output_dir=None, repeat=1):
    db_path = get_db_path(output_dir)
    init_db(db_path)

    update_steps(config)

    # TODO: update tasks, parameters, runs
