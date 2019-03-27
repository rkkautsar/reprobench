import os
import signal
import click
import atexit
import strictyaml
import time
from loguru import logger
from playhouse.apsw_ext import APSWDatabase
from reprobench.core.schema import schema
from reprobench.core.db import db, Run
from reprobench.utils import import_class


@click.command()
@click.option("-c", "--config", required=True, type=click.File())
@click.option(
    "-d",
    "--database",
    required=True,
    type=click.Path(dir_okay=False, resolve_path=True),
)
@click.argument("run_id", type=int)
def run(config, database, run_id):
    config = config.read()
    config = strictyaml.load(config, schema=schema).data
    db.initialize(APSWDatabase(str(database)))

    with db.atomic("EXCLUSIVE"):
        run = Run.get_by_id(run_id)

    tool = import_class(run.tool.module)
    context = config.copy()
    context["tool"] = tool
    context["run"] = run
    logger.info(f"Processing task: {run['directory']}")

    @atexit.register
    def exit():
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.killpg(os.getpgid(0), signal.SIGTERM)
        time.sleep(3)
        os.killpg(os.getpgid(0), signal.SIGKILL)

    for runstep in config["steps"]["run"]:
        logger.debug(f"Running step {runstep['step']}")
        step = import_class(runstep["step"])
        step.execute(context, runstep.get("config", {}))


if __name__ == "__main__":
    run()
