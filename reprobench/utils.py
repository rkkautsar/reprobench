"""Various utilities"""

import importlib
import re
import tarfile
import zipfile
from ast import literal_eval
from collections.abc import Iterable
from pathlib import Path
from shutil import which

import numpy
import requests
import strictyaml
from reprobench.core.exceptions import ExecutableNotFoundError, NotSupportedError
from reprobench.core.schema import schema
from retrying import retry
from tqdm import tqdm

try:
    import msgpack
    from playhouse.apsw_ext import APSWDatabase
    from reprobench.core.db import db
except ImportError:
    APSWDatabase = None
    db = None


def find_executable(executable):
    """Find an executable path from its name

    Similar to `/usr/bin/which`, this function find the path
    of an executable by its name, for example by finding it in
    the PATH environment variable.

    Args:
        executable (str): The executable name

    Returns:
        str: Path of the executable

    Raises:
        ExecutableNotFoundError: If no path for `executable`
            is found.
    """
    path = which(executable)
    if path is None:
        raise ExecutableNotFoundError
    return path


def import_class(path):
    """Import a class by its path

    Args:
        path (str): the path to the class, in similar notation as modules

    Returns:
        class: the specified class

    Examples:
        >>> import_class("reprobench.core.server.BenchmarkServer")
        <class 'reprobench.core.server.BenchmarkServer'>
    """
    module_path, tail = ".".join(path.split(".")[:-1]), path.split(".")[-1]
    module = importlib.import_module(module_path)
    return getattr(module, tail)


def _copy_file_obj(source, destination, callback, length=16 * 1024):
    """Modified version of shutil.copyfileobj with callback"""
    while True:
        buf = source.read(length)
        if not buf:
            break
        destination.write(buf)
        callback(len(buf))


def download_file(url, dest):
    """Download a file by the specified URL

    Args:
        url (str): URL for the file to download
        dest (str): Destination path for saving the file
    """
    r = requests.get(url, stream=True)

    with tqdm(
        total=int(r.headers.get("content-length", 0)),
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        progress_bar.set_postfix(file=Path(dest).name, refresh=False)
        with open(dest, "wb") as f:
            _copy_file_obj(r.raw, f, progress_bar.update)


ranged_numbers_re = re.compile(r"(?P<start>\d+)\.\.(?P<end>\d+)(\.\.(?P<step>\d+))?")


def is_range_str(range_str):
    """Check if a string is in range notation

    Args:
        range_str (str): The string to check

    Returns:
        bool: if the string is in range notation

    Examples:
        >>> is_range_str("1..2")
        True
        >>> is_range_str("1..5..2")
        True
        >>> is_range_str("1")
        False
    """
    return ranged_numbers_re.match(range_str) is not None


def str_to_range(range_str):
    """Generate range from a string with range notation

    Args:
        range_str (str): The string with range notation

    Returns:
        range: The generated range

    Examples:
        >>> str_to_range("1..3")
        range(1, 4)
        >>> str_to_range("1..5..2")
        range(1, 6, 2)
        >>> [*str_to_range("1..3")]
        [1, 2, 3]
    """
    matches = ranged_numbers_re.match(range_str).groupdict()
    start = int(matches["start"])
    end = int(matches["end"]) + 1

    if matches["step"]:
        return range(start, end, int(matches["step"]))
    return range(start, end)


def encode_message(obj):
    """Encode an object for transport

    This method serialize the object with msgpack for
    network transportation.

    Args:
        obj: serializable object

    Returns:
        bin: binary string of the encoded object
    """
    return msgpack.packb(obj, use_bin_type=True)


def decode_message(msg):
    """Decode an encoded object

    This method deserialize the encoded object from
    `encode_message(obj)`.

    Args:
        bin: binary string of the encoded object

    Returns:
        obj: decoded object
    """
    return msgpack.unpackb(msg, raw=False)


@retry(wait_exponential_multiplier=500)
def send_event(socket, event_type, payload=None):
    """Used in the worker with a DEALER socket to send events to the server.

    Args:
        socket (zmq.Socket): the socket for sending the event
        event_type (str): event type agreed between the parties
        payload (any, optional): the payload for the event
    """
    event = [event_type, encode_message(payload)]
    socket.send_multipart(event)


def recv_event(socket):
    """Receive published event for the observers

    Args:
        socket (zmq.Socket): SUB socket for receiving the event

    Returns:
        (event_type, payload, address): Tuple for received events
    """
    event_type, payload, address = socket.recv_multipart()

    return event_type, decode_message(payload), address


def get_db_path(output_dir):
    """Get the database path from the given output directory

    Args:
        output_dir (str): path to the output directory

    Returns:
        str: database path
    """
    return str((Path(output_dir) / f"benchmark.db").resolve())


def init_db(db_path):
    """Initialize the given database

    Args:
        db_path (str): path to the database
    """
    database = APSWDatabase(db_path, pragmas=(("journal_mode", "wal"),))
    db.initialize(database)


def resolve_files_uri(root):
    """Resolve all `file://` URIs in a dictionary to its content

    Args:
        root (dict): Root dictionary of the configuration

    Examples:
        >>> d = dict(test="file://./test.txt")
        >>> resolve_files_uri(d)
        >>> d
        {'a': 'this is the content of test.txt\\n'}
    """
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
    """Read a YAML configuration from a path

    Args:
        config_path (str): Configuration file path (YAML)
        resolve_files (bool, optional): Should files be resolved to its content? Defaults to False.

    Returns:
        dict: Configuration
    """
    with open(config_path, "r") as f:
        config_text = f.read()
        config = strictyaml.load(config_text, schema=schema).data

    if resolve_files:
        resolve_files_uri(config)

    return config


def extract_zip(path, dest):
    """Extract a ZIP file

    Args:
        path (str): Path to ZIP file
        dest (str): Destination for extraction
    """
    if not dest.is_dir():
        with zipfile.ZipFile(path, "r") as f:
            f.extractall(dest)


def extract_tar(path, dest):
    """Extract a TAR file

    Args:
        path (str): Path to TAR file
        dest (str): Destination for extraction
    """
    if not dest.is_dir():
        with tarfile.TarFile.open(path) as f:
            f.extractall(dest)


def extract_archives(path):
    """Extract archives based on its extension

    Args:
        path (str): Path to the archive file
    """
    extract_path = Path(path).with_name(path.stem)

    if zipfile.is_zipfile(path):
        extract_zip(path, extract_path)
    elif tarfile.is_tarfile(path):
        extract_tar(path, extract_path)


def get_pcs_parameter_range(parameter_str, is_categorical):
    """Generate a range from specified pcs range notation

    Args:
        parameter_str (str): specified pcs parameter
        is_categorical (bool): is the range categorical

    Raises:
        NotSupportedError: If there is no function for resolving the range

    Returns:
        range: Generated range
    """
    functions = dict(
        range=range,
        arange=numpy.arange,
        linspace=numpy.linspace,
        logspace=numpy.logspace,
        geomspace=numpy.geomspace,
    )

    function_re = re.compile(r"(?P<function>[A-Za-z_]+)\((?P<arguments>.*)\)")

    match = function_re.match(parameter_str)

    parameter_range = None
    if match:
        function = match.group("function")
        if function not in functions:
            raise NotSupportedError(f"Declaring range with {function} is not supported")
        args = literal_eval(match.group("arguments"))
        parameter_range = functions[function](*args)
    else:
        parameter_range = literal_eval(parameter_str)
        if not isinstance(parameter_range, Iterable) or isinstance(
            parameter_range, str
        ):
            parameter_range = (parameter_range,)
        if is_categorical:
            parameter_range = map(str, parameter_range)

    return parameter_range


def parse_pcs_parameters(lines):
    """Parse parameters from a pcs file content

    Args:
        lines ([str]): pcs file content

    Returns:
        dict: generated parameters
    """
    parameter_range_indicator = "-->"

    parameters = {}
    parameter_key = None
    is_categorical = False

    for line in lines:
        if ("{" in line or "[" in line) and not line.startswith("#"):
            parameter_key = line[: line.find(" ")]
            is_categorical = "{" in line

        if "#" not in line or parameter_range_indicator not in line:
            continue

        comment_pos = line.find("#")
        pos = line.find(parameter_range_indicator, comment_pos)
        parameter_str = line[pos + len(parameter_range_indicator) :].strip()

        parameter_range = get_pcs_parameter_range(parameter_str, is_categorical)

        parameters[parameter_key] = parameter_range

    return parameters


def check_valid_config_space(config_space, parameters):
    """Check if the parameters is valid based on a configuration space

    Args:
        config_space (ConfigSpace): configuration space
        parameters (dict): parameters dictionary

    Raises:
        ValueError: If there is invalid values
    """
    base = config_space.get_default_configuration()
    for key, value in parameters.items():
        if key in base:
            base[key] = value

