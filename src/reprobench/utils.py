import importlib
import subprocess
from reprobench.core.exceptions import ExecutableNotFoundError
from shutil import which

def find_executable(executable):
    path = which(executable)
    if path is None:
        raise ExecutableNotFoundError
    return path

def silent_run(command):
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def import_class(path):
    module_path, tail = '.'.join(path.split('.')[:-1]), path.split('.')[-1]
    module = importlib.import_module(module_path)
    return getattr(module, tail)
