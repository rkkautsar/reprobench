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


from loguru import logger
from playhouse.apsw_ext import APSWDatabase
from tqdm import tqdm

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.db import Run, db
from reprobench.core.server import BenchmarkServer
from reprobench.task_sources.local import LocalSource
from reprobench.utils import import_class

from .worker import execute


class LocalRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir", "./output")
        self.resume = kwargs.pop("resume", False)
        self.server_address = kwargs.pop("server_address", "tcp://127.0.0.1:31313")
        self.observers = []
        self.queue = []

    def setup(self):
        atexit.register(self.exit)
        self.setup_finished = False

        self.db_path = Path(self.output_dir) / f"{self.config['title']}.benchmark.db"
        db_created = Path(self.db_path).is_file()

        for observer in self.config["observers"]:
            self.observers.append(import_class(observer["module"]))

        if db_created and not self.resume:
            logger.error(
                "It seems that a previous runs already exist at the output directory.\
                Please use --resume to resume unfinished runs."
            )
            self.setup_finished = True
            exit(1)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using Database: {self.db_path}")
        self.database = APSWDatabase(str(self.db_path))
        db.initialize(self.database)

        # TODO: maybe use .bootstrapped file instead?
        if not db_created:
            bootstrap(self.config, self.output_dir)

        self.setup_finished = True

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
        self.setup()
        self.populate_unfinished_runs()
        db.close()

        if len(self.queue) == 0:
            logger.success("No tasks remaining to run")
            exit(0)

        logger.debug("Executing runs...")

        server = BenchmarkServer(
            self.observers, str(self.db_path), address=self.server_address
        )

        server.start()

        with Pool() as pool:
            it = pool.imap_unordered(execute, self.queue)
            progress_bar = tqdm(desc="Executing runs", total=len(self.queue))
            for _ in it:
                progress_bar.update()
            progress_bar.close()

        server.join()

        logger.debug("Running teardown on all tools...")
        for tool in self.config["tools"].values():
            import_class(tool["module"]).teardown()
