import atexit
import itertools
import os
import shutil
import signal
import time
from datetime import datetime
from multiprocessing.pool import Pool
from pathlib import Path

from loguru import logger
from playhouse.apsw_ext import APSWDatabase
from tqdm import tqdm

from reprobench.core.bases import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.core.db import ParameterCategory, Run, Task, Tool, db
from reprobench.task_sources.local import LocalSource
from reprobench.utils import import_class


def execute_run(args):
    run_id, config, db_path = args

    run = Run.get_by_id(run_id)
    ToolClass = import_class(run.tool.module)
    tool_instance = ToolClass()
    db.initialize(APSWDatabase(str(db_path)))
    context = config.copy()
    context["tool"] = tool_instance
    context["run"] = run
    logger.info(f"Processing task: {run.directory}")

    @atexit.register
    def exit():
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.killpg(os.getpgid(0), signal.SIGTERM)
        time.sleep(3)
        os.killpg(os.getpgid(0), signal.SIGKILL)

    for runstep in config["steps"]["run"]:
        Step = import_class(runstep["step"])
        Step.execute(context, runstep.get("config", {}))


class LocalRunner(Runner):
    def __init__(self, config, output_dir="./output", resume=False):
        self.config = config
        self.output_dir = output_dir
        self.resume = resume
        self.queue = []

    def setup(self):
        atexit.register(self.exit)
        self.setup_finished = False

        self.db_path = Path(self.output_dir) / f"{self.config['title']}.benchmark.db"
        db_created = Path(self.db_path).is_file()

        if db_created and not self.resume:
            logger.error(
                "It seems that a previous runs already exist at the output directory.\
                Please use --resume to resume unfinished runs."
            )
            self.setup_finished = True
            exit(1)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Creating Database: {self.db_path}")
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
        self.queue = [(run.id, self.config, self.db_path) for run in query]

    def run(self):
        self.setup()
        self.populate_unfinished_runs()

        if len(self.queue) == 0:
            logger.success("No tasks remaining to run")
            exit(0)

        logger.debug("Executing runs...")

        self.pool = Pool()
        it = self.pool.imap_unordered(execute_run, self.queue)
        num_in_queue = len(self.queue)
        for _ in tqdm(it, total=num_in_queue):
            num_in_queue -= 1

        self.pool.close()
        self.pool.join()

        logger.debug("Running teardown on all tools...")
        for tool in self.config["tools"].values():
            import_class(tool).teardown()

