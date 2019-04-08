import json

import click
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.console.decorators import common
from reprobench.core.db import Step, db
from reprobench.utils import get_db_path, import_class


class BenchmarkAnalyzer(object):
    def __init__(self, output_dir, **kwargs):
        self.output_dir = output_dir
        self.db_path = get_db_path(output_dir)
        db.initialize(APSWDatabase(self.db_path))

    def run(self):
        steps = Step.select().where(Step.category == Step.ANALYSIS)
        context = dict(output_dir=self.output_dir, db_path=self.db_path)
        for step in steps:
            logger.debug(f"Running {step.module}")
            module = import_class(step.module)
            config = json.loads(step.config)
            module.execute(context, config)


@click.command(name="analyze")
@click.option(
    "-d", "--output-dir", type=click.Path(), default="./output", show_default=True
)
@common
def cli(output_dir, **kwargs):
    analyzer = BenchmarkAnalyzer(output_dir, **kwargs)
    analyzer.run()


if __name__ == "__main__":
    cli()
