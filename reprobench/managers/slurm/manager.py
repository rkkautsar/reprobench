import math
import subprocess
import sys

from loguru import logger

from reprobench.managers.base import BaseManager
from reprobench.utils import read_config

from .utils import to_comma_range


class SlurmManager(BaseManager):
    BATCH = 256  # maximum number of task to execute at one time

    def __init__(self, config, output_dir, **kwargs):
        super().__init__(**kwargs)
        self.config = read_config(config)
        self.output_dir = output_dir

    def prepare(self):
        limits = self.config["limits"]
        time_limit_minutes = int(math.ceil(limits["time"] / 60.0))

        self.cpu_count = limits.get("cores", 1)
        # @TODO improve this
        self.time_limit = 2 * time_limit_minutes
        self.mem_limit = 2 * limits["memory"]

    def stop(self):
        subprocess.run(["scancel", f"--name={self.config['title']}-benchmark-worker"])

    def spawn_workers(self):
        logger.info("Spawning workers...")
        worker_cmd = f"{sys.exec_prefix}/bin/reprobench worker --address={self.server_address} -vv"
        worker_submit_cmd = [
            "sbatch",
            "--parsable",
            f"--array={to_comma_range(self.queue)}%{self.BATCH}",
            f"--time={self.time_limit}",
            f"--mem={self.mem_limit}",
            f"--cpus-per-task={self.cpu_count}",
            f"--job-name={self.config['title']}-benchmark-worker",
            f"--output={self.output_dir}/slurm-worker_%a.out",
            "--wrap",
            f"srun {worker_cmd} $SLURM_ARRAY_TASK_ID",
        ]
        logger.trace(worker_submit_cmd)
        self.worker_job = subprocess.check_output(worker_submit_cmd).decode().strip()
        logger.info(f"Worker job array id: {self.worker_job}")
