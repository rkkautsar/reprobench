import atexit
import time
from multiprocessing import Process, cpu_count
from pathlib import Path

import click
from loguru import logger

from reprobench.core.server import BenchmarkServer
from reprobench.core.worker import BenchmarkWorker
from reprobench.runners.base import BaseRunner
from reprobench.utils import read_config


class LocalRunner(BaseRunner):
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.num_workers = kwargs.pop("num_workers") or cpu_count()
        self.start_time = None
        self.workers = []
        port = kwargs.pop("port")
        host = kwargs.pop("host")
        self.server_address = f"tcp://{host}:{port}"

    def exit(self):
        if hasattr(self, "server_proc"):
            self.server_proc.terminate()
            self.server_proc.join()

        for worker in self.workers:
            worker.terminate()
            worker.join()

        logger.info(f"Total time elapsed: {time.perf_counter() - self.start_time}")

    def prepare(self):
        atexit.register(self.exit)
        self.start_time = time.perf_counter()

    def spawn_server(self):
        server = BenchmarkServer(self.db_path, self.server_address)
        self.server_proc = Process(target=server.run)
        self.server_proc.start()

    def spawn_workers(self):
        worker = BenchmarkWorker(self.server_address)
        for _ in range(self.num_workers):
            worker_proc = Process(target=worker.run)
            worker_proc.start()
            self.workers.append(worker_proc)

    def wait(self):
        self.server_proc.join()
        for worker in self.workers:
            worker.join()


@click.command("local")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    show_default=True,
)
@click.option("--resume", is_flag=True, default=False)
@click.option("-w", "--num-workers", type=int)
@click.option("-h", "--host", default="127.0.0.1", show_default=True)
@click.option("-p", "--port", default=31313, show_default=True)
@click.argument("config", type=click.Path())
def cli(config, **kwargs):
    config = read_config(config)
    runner = LocalRunner(config, **kwargs)
    runner.run()


if __name__ == "__main__":
    cli()
