import time
from pathlib import Path

from loguru import logger

from reprobench.core.base import Runner
from reprobench.core.bootstrap import bootstrap
from reprobench.utils import get_db_path


class BaseRunner(Runner):
    def __init__(self, config, **kwargs):
        self.config = config
        self.output_dir = kwargs.pop("output_dir")
        self.resume = kwargs.pop("resume", False)
        self.num_workers = kwargs.pop("num_workers", None)
        self.db_path = get_db_path(self.output_dir)

    def prepare(self):
        pass

    def spawn_server(self):
        raise NotImplementedError

    def spawn_workers(self):
        raise NotImplementedError

    def wait(self):
        pass

    def run(self):
        db_exist = Path(self.db_path).exists()

        if not db_exist:
            bootstrap(self.config, self.output_dir)

        if db_exist and not self.resume:
            logger.warning(
                f"Previous run exists in {self.output_dir}. Please use --resume, or specify a different output directory"
            )
            exit(1)

        self.prepare()
        self.spawn_server()
        logger.info("Sleeping for 3s, making sure the server has started...")
        time.sleep(3)
        self.spawn_workers()
        self.wait()
