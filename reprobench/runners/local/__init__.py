import atexit
import time
from multiprocessing import Process, cpu_count
from pathlib import Path

import click
from loguru import logger

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.server import BenchmarkServer
from reprobench.core.worker import BenchmarkWorker
from reprobench.task_sources.local import LocalSource
from reprobench.utils import get_db_path, import_class, read_config


class LocalRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir", "./output")
        self.num_workers = kwargs.pop("num_workers") or cpu_count()
        self.resume = kwargs.pop("resume")
        self.db_path = get_db_path(self.output_dir)
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

    def run(self):
        atexit.register(self.exit)
        self.start_time = time.perf_counter()

        db_exist = Path(self.db_path).exists()

        if not db_exist:
            bootstrap(self.config, self.output_dir)

        if db_exist and not self.resume:
            logger.warning(
                f"Previous run exists in {self.output_dir}. Please use --resume, or specify a different output directory"
            )
            exit(1)

        server = BenchmarkServer(self.db_path, self.server_address)
        self.server_proc = Process(target=server.run)
        self.server_proc.start()

        worker = BenchmarkWorker(self.server_address)
        for _ in range(self.num_workers):
            worker_proc = Process(target=worker.run)
            worker_proc.start()
            self.workers.append(worker_proc)

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
