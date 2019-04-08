import importlib
import re
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from shutil import which

import requests
import strictyaml
from tqdm import tqdm

from reprobench.core.db import db
from reprobench.core.exceptions import ExecutableNotFoundError
from reprobench.core.schema import schema

try:
    import msgpack
    from playhouse.apsw_ext import APSWDatabase
except ImportError:
    pass


def find_executable(executable):
    path = which(executable)
    if path is None:
        raise ExecutableNotFoundError
    return path


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
        total=int(r.headers.get("content-length", 0)),
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        progress_bar.set_postfix(file=Path(dest).name, refresh=False)
        with open(dest, "wb") as f:
            copyfileobj(r.raw, f, progress_bar.update)


ranged_numbers_re = re.compile(r"(?P<start>\d+)\.\.(?P<end>\d+)(\.\.(?P<step>\d+))?")


def is_range_str(range_str):
    return ranged_numbers_re.match(range_str)


def str_to_range(range_str):
    matches = ranged_numbers_re.match(range_str).groupdict()
    start = int(matches["start"])
    end = int(matches["end"])

    if matches["step"]:
        return range(start, end, int(matches["step"]))
    return range(start, end)


def encode_message(obj):
    return msgpack.packb(obj, use_bin_type=True)


def decode_message(msg):
    return msgpack.unpackb(msg, raw=False)


def send_event(socket, event_type, payload=None):
    """
    Used in the worker with a DEALER socket
    """
    socket.send_multipart([event_type, encode_message(payload)])


def recv_event(socket):
    """
    Used in the SUB handler
    """
    event_type, payload, address = socket.recv_multipart()

    return event_type, decode_message(payload), address


def get_db_path(output_dir):
    return str((Path(output_dir) / f"benchmark.db").resolve())


def init_db(db_path):
    database = APSWDatabase(db_path)
    db.initialize(database)


def resolve_files_uri(root):
    protocol = "file://"
    iterator = None
    if isinstance(root, dict):
        iterator = root
    elif isinstance(root, list) or isinstance(root, tuple):
        iterator = range(len(root))

    for k in iterator:
        if isinstance(root[k], str) and root[k].startswith(protocol):
            root[k] = Path(root[k][len(protocol) :]).read_text()
        elif isinstance(root[k], Iterable) and not isinstance(root[k], str):
            resolve_files_uri(root[k])


def read_config(config_path, resolve_files=False):
    with open(config_path, "r") as f:
        config_text = f.read()
        config = strictyaml.load(config_text, schema=schema).data

    if resolve_files:
        resolve_files_uri(config)

    return config


def extract_zip(path, dest):
    if not dest.is_dir():
        with zipfile.ZipFile(path, "r") as f:
            f.extractall(dest)


def extract_tar(path, dest):
    if not dest.is_dir():
        with tarfile.TarFile.open(path) as f:
            f.extractall(dest)


def extract_archives(path):
    extract_path = Path(path).with_name(path.stem)

    if zipfile.is_zipfile(path):
        extract_zip(path, extract_path)
    elif tarfile.is_tarfile(path):
        extract_tar(path, extract_path)
