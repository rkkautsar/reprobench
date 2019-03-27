import atexit
import os
from signal import signal

import zmq
from loguru import logger
from playhouse.apsw_ext import APSWDatabase

from reprobench.core.db import Run, db
from reprobench.core.events import RUN_REGISTER, RUN_COMPLETE
from reprobench.utils import import_class, decode_message, send_event


def clean_up():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.killpg(os.getpgid(0), signal.SIGTERM)
    time.sleep(1)
    os.killpg(os.getpgid(0), signal.SIGKILL)


def execute(args):
    atexit.register(clean_up)

    run_id, config, server_address = args

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(server_address)
    send_event(socket, RUN_REGISTER, run_id)
    run = decode_message(socket.recv())
    tool = import_class(run["tool"])
    context = config.copy()
    context["tool"] = tool
    context["run"] = run
    context["socket"] = socket
    logger.info(f"Processing task: {run['directory']}")

    for runstep in config["steps"]["run"]:
        logger.debug(f"Running step {runstep['module']}")
        step = import_class(runstep["module"])
        step.execute(context, runstep.get("config", {}))

    send_event(socket, RUN_COMPLETE, run_id)
