import subprocess
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from reprobench.core.bases import Tool
from reprobench.utils import find_executable, silent_run


class ExecutableTool(Tool):
    name = "Basic Executable Tool"
    path = None

