import time

import click
from tqdm import tqdm

from reprobench.core.db import Run
from reprobench.utils import init_db


def get_total_count():
    return Run.select().count()


def get_done_count():
    return Run.select().where(Run.status == Run.DONE).count()


@click.command("status")
@click.option("-d", "--database", default="./output/benchmark.db", show_default=True)
@click.option("-n", "--interval", default=2, show_default=True, type=int)
def benchmark_status(database, interval):
    init_db(database)
    total = get_total_count()

    last = get_done_count()
    progress = tqdm(total=total, initial=last)

    while last < total:
        time.sleep(interval)
        current = get_done_count()
        progress.update(current - last)
        last = current
