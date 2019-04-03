import math
import subprocess
import sys
from pathlib import Path

from loguru import logger

from reprobench.core.db import Run
from reprobench.runners.base import BaseRunner
from reprobench.utils import init_db

from .utils import get_nodelist


class SlurmRunner(BaseRunner):
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.port = kwargs.pop("port")
        self.num_workers = kwargs.pop("num_workers", None)

    def prepare(self):
        init_db(self.db_path)
        limits = self.config["limits"]
        num_jobs = Run.select(Run.id).where(Run.status < Run.DONE).count()
        jobs_per_worker = int(math.ceil(1.0 * num_jobs / self.num_workers))
        time_limit_minutes = int(math.ceil(limits["time"] / 60.0))

        self.cpu_count = limits.get("cores", 1)
        # @TODO improve this
        self.time_limit = 2 * time_limit_minutes * jobs_per_worker
        self.mem_limit = 2 * limits["memory"]

    def stop(self):
        subprocess.run(["scancel", f"--name={self.config['title']}-benchmark-server"])
        subprocess.run(["scancel", f"--name={self.config['title']}-benchmark-worker"])

    def spawn_server(self):
        logger.info("Spawning server...")
        server_cmd = f"{sys.exec_prefix}/bin/reprobench -vvv server --database={self.db_path} --port={self.port}"
        server_submit_cmd = [
            "sbatch",
            "--parsable",
            f"--time={self.time_limit}",
            f"--job-name={self.config['title']}-benchmark-server",
            f"--output={self.output_dir}/slurm-server.out",
            "--wrap",
            server_cmd,
        ]
        logger.debug(server_submit_cmd)
        self.server_job = subprocess.check_output(server_submit_cmd).decode().strip()
        logger.info("Waiting for the server to be assigned...")
        self.server_host = get_nodelist(self.server_job)
        logger.info(f"Server spawned at {self.server_host}, job id: {self.server_job}")
        self.server_address = f"tcp://{self.server_host}:{self.port}"

    def spawn_workers(self):
        logger.info("Spawning workers...")
        worker_cmd = f"{sys.exec_prefix}/bin/reprobench -vvv worker --host={self.server_host} --port={self.port}"
        worker_submit_cmd = [
            "sbatch",
            "--parsable",
            f"--ntasks={self.num_workers}",
            f"--time={self.time_limit}",
            f"--mem={self.mem_limit}",
            f"--cpus-per-task={self.cpu_count}",
            f"--job-name={self.config['title']}-benchmark-worker",
            f"--output={self.output_dir}/slurm-worker.out",
            "--wrap",
            f"srun {worker_cmd}",
        ]
        logger.debug(worker_submit_cmd)
        self.worker_job = subprocess.check_output(worker_submit_cmd).decode().strip()
        logger.info(f"Workers job id: {self.worker_job}")
