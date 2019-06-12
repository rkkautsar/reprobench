import math
import subprocess
import sys
from pathlib import Path

from loguru import logger

from sshtunnel import SSHTunnelForwarder
from reprobench.managers.base import BaseManager
from reprobench.utils import read_config

from .utils import to_comma_range


class SlurmManager(BaseManager):
    def prepare(self):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        limits = self.config["limits"]
        time_limit_minutes = int(math.ceil(limits["time"] / 60.0))

        self.cpu_count = limits.get("cores", 1)
        # @TODO improve this
        self.time_limit = 2 * time_limit_minutes
        self.mem_limit = 2 * limits["memory"]

        if self.tunneling is not None:
            self.server = SSHTunnelForwarder(
                self.tunneling["host"],
                remote_bind_address=("127.0.0.1", self.tunneling["port"]),
                ssh_pkey=self.tunneling["key_file"],
                ssh_config_file=self.tunneling["ssh_config_file"],
            )

            # https://github.com/pahaz/sshtunnel/issues/138
            if sys.version_info[0] > 3 or (
                sys.version_info[0] == 3 and sys.version_info[1] >= 7
            ):
                self.server.daemon_forward_servers = True

            self.server.start()
            self.server_address = f"tcp://127.0.0.1:{self.server.local_bind_port}"
            logger.info(f"Tunneling established at {self.server_address}")

    def stop(self):
        subprocess.run(["scancel", f"--name={self.config['title']}-benchmark-worker"])

    def spawn_workers(self):
        logger.info("Spawning workers...")

        address_args = f"--address={self.server_address}"
        if self.tunneling is not None:
            address_args = f"-h {self.tunneling['host']} -p {self.tunneling['port']} -K {self.tunneling['key_file']}"

        worker_cmd = f"{sys.exec_prefix}/bin/reprobench worker {address_args} -vv"
        worker_submit_cmd = [
            "sbatch",
            "--parsable",
            f"--array=1-{self.pending}",
            f"--time={self.time_limit}",
            f"--mem={self.mem_limit}",
            f"--cpus-per-task={self.cpu_count}",
            f"--job-name={self.config['title']}-benchmark-worker",
            f"--output={self.output_dir}/slurm-worker_%a.out",
            "--wrap",
            f"srun {worker_cmd}",
        ]
        logger.trace(worker_submit_cmd)
        self.worker_job = subprocess.check_output(worker_submit_cmd).decode().strip()
        logger.info(f"Worker job array id: {self.worker_job}")

    def wait(self):
        if self.tunneling is not None:
            self.server.stop()

