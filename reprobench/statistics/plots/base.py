from pathlib import Path

import papermill as pm

from reprobench.core.base import Step


class NotebookExecutor(Step):
    INPUT_NOTEBOOK = None
    DEFAULT_OUTPUT = None

    @classmethod
    def execute(cls, context, config=None):
        if config is None:
            config = {}

        output_dir = context.get("output_dir", None)
        output = Path(output_dir) / config.get("output", cls.DEFAULT_OUTPUT)
        output.parent.mkdir(parents=True, exist_ok=True)

        parameters = dict(db_path=context.get("db_path"), **config)
        pm.execute_notebook(cls.INPUT_NOTEBOOK, str(output), parameters=parameters)

