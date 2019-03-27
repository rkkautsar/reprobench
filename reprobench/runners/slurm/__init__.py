import itertools
import os
import signal
import subprocess
import time
from multiprocessing.pool import Pool
from pathlib import Path
from string import Template

import click
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.db import Run, db
from reprobench.utils import get_db_path, import_class, init_db, read_config

from .utils import create_ranges

DIR = os.path.dirname(os.path.realpath(__file__))


class SlurmRunner(Runner):
    def __init__(self, config_path, python_path, server_address, **kwargs):
        self.config = read_config(config_path)
        self.config_path = config_path
        self.python_path = python_path
        self.server_address = server_address
        self.output_dir = kwargs.pop("output_dir", "./output")
        self.resume = kwargs.pop("resume", False)
        self.templates = {}
        self.templates["server"] = kwargs.pop(
            "server_template_file", os.path.join(DIR, "./slurm.server.job.tpl")
        )
        self.templates["run"] = kwargs.pop(
            "run_template_file", os.path.join(DIR, "./slurm.run.job.tpl")
        )
        self.templates["compile"] = kwargs.pop(
            "compile_template_file", os.path.join(DIR, "./slurm.compile.job.tpl")
        )
        self.queue = []

    def populate_unfinished_runs(self):
        query = Run.select(Run.id).where(Run.status < Run.DONE)
        self.queue = [run.id for run in query]

    def generate_template(self, template_type):
        template_file = self.templates[template_type]
        with open(template_file) as tpl:
            template = Template(tpl.read())
            job_str = template.safe_substitute(
                output_dir=self.output_dir,
                mem=int(1 + self.config["limits"]["memory"] / 1024 / 1024),  # mb
                time=int(1 + (self.config["limits"]["time"] + 15) / 60),  # minutes
                run_ids=create_ranges(self.queue),
                python_path=self.python_path,
                config_path=self.config_path,
                server_address=self.server_address,
            )

        job_path = Path(self.output_dir) / f"slurm.{template_type}.job"
        with open(job_path, "w") as job:
            job.write(job_str)

        return str(job_path.resolve())

    def run(self):
        init_db(get_db_path(self.output_dir))
        self.populate_unfinished_runs()
        db.close()

        if len(self.queue) == 0:
            logger.success("No tasks remaining to run")
            exit(0)

        logger.debug("Generating templates...")
        templates = {t: self.generate_template(t) for t in ["run"]}

        logger.info("Submitting jobs to SLURM...")

        run_cmd = ["sbatch", "--parsable", templates["run"]]
        run_job = subprocess.check_output(run_cmd).decode().strip()
        logger.debug(f"Run job id: {run_job}")


@click.command("slurm")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    required=True,
    show_default=True,
)
@click.option("--run-template", type=click.Path(dir_okay=False, resolve_path=True))
@click.option("--compile-template", type=click.Path(dir_okay=False, resolve_path=True))
@click.option("-r", "--resume", is_flag=True)
@click.option("-p", "--python-path", required=True, type=click.Path(resolve_path=True))
@click.option("-s", "--server", required=True)
@click.argument("config", type=click.Path())
def cli(config, output_dir, python_path, server, **kwargs):
    runner = SlurmRunner(
        config_path=config, python_path=python_path, server_address=server, **kwargs
    )
    runner.run()


if __name__ == "__main__":
    cli()
