import math
import os
import signal
import subprocess
import sys
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
from reprobench.runners.slurm.utils import get_nodelist
from reprobench.utils import get_db_path, import_class, init_db, read_config

from .utils import create_ranges

DIR = os.path.dirname(os.path.realpath(__file__))


class SlurmRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir")
        self.resume = kwargs.pop("resume", False)
        self.port = kwargs.pop("port")
        self.num_workers = kwargs.pop("num_workers", None)
        self.db_path = get_db_path(self.output_dir)

    def spawn_server(self, time_limit):
        logger.info("Spawning server...")
        server_cmd = f"{sys.exec_prefix}/bin/reprobench -vvv server --database={self.db_path} --port={self.port}"
        server_submit_cmd = [
            "sbatch",
            "--parsable",
            f"--time={time_limit}",
            f"--job-name={self.config['title']}-benchmark-server",
            f"--output={self.output_dir}/slurm-server.out",
            "--wrap",
            server_cmd,
        ]
        logger.debug(server_submit_cmd)
        server_job = subprocess.check_output(server_submit_cmd).decode().strip()
        logger.info("Waiting for the server to be assigned...")
        server_host = get_nodelist(server_job)
        logger.info(f"Server spawned at {server_host}, job id: {server_job}")

        return server_host

    def spawn_workers(self, server_host, time_limit, mem_limit):
        logger.info("Spawning workers...")
        worker_cmd = f"{sys.exec_prefix}/bin/reprobench -vvv worker --host={server_host} --port={self.port}"
        worker_submit_cmd = [
            "sbatch",
            "--parsable",
            f"--ntasks={self.num_workers}",
            f"--time={time_limit}",
            f"--mem={mem_limit}",
            f"--job-name={self.config['title']}-benchmark-worker",
            f"--output={self.output_dir}/slurm-worker.out",
            "--wrap",
            f"srun {worker_cmd}",
        ]
        logger.debug(worker_submit_cmd)
        worker_job = subprocess.check_output(worker_submit_cmd).decode().strip()
        logger.info(f"Workers job id: {worker_job}")

        return worker_job

    def run(self):
        db_exist = Path(self.db_path).exists()

        if not db_exist:
            bootstrap(self.config, self.output_dir)

        if db_exist and not self.resume:
            logger.warning(
                f"Previous run exists in {self.output_dir}. Please use --resume, or specify a different output directory"
            )
            exit(1)

        init_db(self.db_path)
        limits = self.config["limits"]
        num_jobs = Run.select(Run.id).where(Run.status < Run.DONE).count()
        jobs_per_worker = int(math.ceil(num_jobs / self.num_workers))

        # @TODO improve this
        time_limit = 2 * limits["time"] * jobs_per_worker
        mem_limit = 2 * limits["memory"]

        server_host = self.spawn_server(time_limit)
        logger.info("Sleeping for 3s...")
        time.sleep(3)
        self.spawn_workers(server_host, time_limit, mem_limit)


@click.command("slurm")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    show_default=True,
)
@click.option("--resume", is_flag=True, default=False)
@click.option("-w", "--num-workers", type=int, required=True)
@click.option("-p", "--port", default=31313, show_default=True)
@click.argument("config", type=click.Path())
def cli(config, **kwargs):
    config = read_config(config)
    runner = SlurmRunner(config, **kwargs)
    runner.run()


if __name__ == "__main__":
    cli()
