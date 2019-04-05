import atexit
import time
from multiprocessing import Pool

from loguru import logger
from tqdm import tqdm

from reprobench.core.worker import BenchmarkWorker
from reprobench.managers.base import BaseManager


class LocalManager(BaseManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.num_workers = kwargs.pop("num_workers")
        self.start_time = None
        self.workers = []

    def exit(self):
        for worker in self.workers:
            worker.terminate()
            worker.join()

        logger.info(f"Total time elapsed: {time.perf_counter() - self.start_time}")

    def prepare(self):
        atexit.register(self.exit)
        self.start_time = time.perf_counter()

    @staticmethod
    def spawn_worker(job):
        server_address, run_id = job
        worker = BenchmarkWorker(server_address, run_id)
        worker.run()

    def spawn_workers(self):
        self.pool = Pool(self.num_workers)
        jobs = ((self.server_address, run_id) for run_id in self.queue)
        self.pool_iterator = self.pool.imap_unordered(self.spawn_worker, jobs)
        self.pool.close()

    def wait(self):
        progress_bar = tqdm(desc="Executing runs", total=len(self.queue))
        for _ in self.pool_iterator:
            progress_bar.update()
        progress_bar.close()
        self.pool.join()
