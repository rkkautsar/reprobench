import os
import signal
import itertools
import time
import subprocess
from string import Template
from loguru import logger
from multiprocessing.pool import Pool
from pathlib import Path
from playhouse.apsw_ext import APSWDatabase
from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.db import db, Run
from reprobench.utils import import_class

from .utils import create_ranges

DIR = os.path.dirname(os.path.realpath(__file__))


class SlurmRunner(Runner):
    def __init__(self, config, config_path, python_path, server_address, **kwargs):
        self.config = config
        self.config_path = config_path
        self.python_path = python_path
        self.server_address = server_address
        self.output_dir = kwargs.pop("output_dir", "./output")
        self.resume = kwargs.pop("resume", False)
        self.teardown = kwargs.pop("teardown", False)
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

    def setup(self):
        self.db_path = Path(self.output_dir) / f"{self.config['title']}.benchmark.db"
        db_created = Path(self.db_path).is_file()

        if db_created and not self.resume:
            logger.error(
                "It seems that a previous runs exist at the output directory. Please use --resume to resume runs."
            )
            exit(1)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using Database: {self.db_path}")
        self.database = APSWDatabase(str(self.db_path))
        db.initialize(self.database)

        # TODO: maybe use .bootstrapped file instead?
        if not db_created:
            bootstrap(self.config, self.output_dir)

    def populate_unfinished_runs(self):
        query = Run.select(Run.id).where(Run.status < Run.DONE)
        self.queue = [run.id for run in query]

    def generate_template(template_type):
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
                db_path=self.db_path,
            )

        job_path = Path(self.output_dir) / f"slurm.{template_type}.job"
        with open(job_path, "w") as job:
            job.write(job_str)

        return str(job_path.resolve())

    def run(self):
        if not self.teardown:
            self.setup()
            self.populate_unfinished_runs()
            db.close()

            if len(self.queue) == 0:
                logger.success("No tasks remaining to run")
                exit(0)

            logger.debug("Generating templates...")
            templates = {t: generate_template(t) for t in ["server", "run"]}

            logger.info("Submitting jobs to SLURM...")
            server_cmd = ["sbatch", templates["server"]]
            server_job = subprocess.check_output(server_cmd).decode()
            logger.debug(f"Server job id: {server_job}")

            run_cmd = ["sbatch", f"--depend=after:{server_job}", templates["run"]]
            run_job = subprocess.check_output(run_cmd).decode()
            logger.debug(f"Run job id: {run_job}")
        else:
            logger.debug("Running teardown on all tools...")
            for tool_module in self.config["tools"].values():
                import_class(tool_module).teardown()
