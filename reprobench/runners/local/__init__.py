import atexit
import itertools
import os
import shutil
import signal
import time
from datetime import datetime
from multiprocessing import Process
from multiprocessing.pool import Pool
from pathlib import Path

import click
from loguru import logger
from playhouse.apsw_ext import APSWDatabase
from tqdm import tqdm

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.db import Run, db
from reprobench.core.server import BenchmarkServer
from reprobench.task_sources.local import LocalSource
from reprobench.utils import get_db_path, import_class, init_db, read_config

from .worker import execute


class LocalRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir", "./output")
        self.resume = kwargs.pop("resume", False)
        self.server_address = kwargs.pop("server", "tcp://127.0.0.1:31313")
        self.observers = []
        self.queue = []

    def exit(self):
        if len(self.queue) > 0 and hasattr(self, "pool"):
            self.pool.terminate()
            self.pool.join()

        if not self.resume and not self.setup_finished:
            shutil.rmtree(self.output_dir)

    def populate_unfinished_runs(self):
        query = Run.select(Run.id).where(Run.status < Run.DONE)
        self.queue = [(run.id, self.config, self.server_address) for run in query]

    def run(self):
        init_db(get_db_path(self.output_dir))
        self.populate_unfinished_runs()
        db.close()

        if len(self.queue) == 0:
            logger.success("No tasks remaining to run")
            exit(0)

        logger.debug("Executing runs...")

        with Pool() as pool:
            it = pool.imap_unordered(execute, self.queue)
            progress_bar = tqdm(desc="Executing runs", total=len(self.queue))
            for _ in it:
                progress_bar.update()
            progress_bar.close()

        logger.debug("Running teardown on all tools...")
        for tool in self.config["tools"].values():
            import_class(tool["module"]).teardown()


@click.command("local")
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./output",
    show_default=True,
)
@click.option("-r", "--resume", is_flag=True)
@click.option("-s", "--server", default="tcp://127.0.0.1:31313")
@click.argument("config", type=click.Path())
def cli(config, output_dir, **kwargs):
    config = read_config(config)
    runner = LocalRunner(config, output_dir=output_dir, **kwargs)
    runner.run()


if __name__ == "__main__":
    cli()
