import importlib
import logging
import subprocess
from shutil import which

import requests
from tqdm import tqdm

from reprobench.core.exceptions import ExecutableNotFoundError

log = logging.getLogger(__name__)


def find_executable(executable):
    path = which(executable)
    if path is None:
        raise ExecutableNotFoundError
    return path


def silent_run(command):
    log.debug(f"Running: {command}")
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def import_class(path):
    module_path, tail = ".".join(path.split(".")[:-1]), path.split(".")[-1]
    module = importlib.import_module(module_path)
    return getattr(module, tail)


def copyfileobj(fsrc, fdst, callback, length=16 * 1024):
    while True:
        buf = fsrc.read(length)
        if not buf:
            break
        fdst.write(buf)
        callback(len(buf))


def download_file(url, dest):
    r = requests.get(url, stream=True)

    with tqdm(
        total=int(r.headers["content-length"]),
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        progress_bar.set_postfix(file=dest, refresh=False)
        with open(dest, "wb") as f:
            copyfileobj(r.raw, f, progress_bar.update)
