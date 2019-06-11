import click
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.console.decorators import common
from reprobench.core.db import Step, db
from reprobench.utils import get_db_path, import_class, init_db, read_config


class BenchmarkAnalyzer(object):
    def __init__(self, output_dir, config, **kwargs):
        self.output_dir = output_dir
        self.config = read_config(config)
        self.db_path = get_db_path(output_dir)
        init_db(self.db_path)

    def run(self):
        steps = self.config["steps"]["analysis"]
        context = dict(output_dir=self.output_dir, db_path=self.db_path)
        for step in steps:
            logger.debug(f"Running {step['module']}")
            module = import_class(step["module"])
            module.execute(context, step["config"])


@click.command(name="analyze")
@click.option(
    "-d", "--output-dir", type=click.Path(), default="./output", show_default=True
)
@click.argument("config", type=click.Path(), default="./benchmark.yml")
@common
def cli(**kwargs):
    analyzer = BenchmarkAnalyzer(**kwargs)
    analyzer.run()


if __name__ == "__main__":
    cli()
