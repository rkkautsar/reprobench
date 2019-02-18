import subprocess
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from reprobench.core.bases import Tool
from reprobench.utils import find_executable, silent_run


class ReprozipTool(Tool):
    name = "Reprozip-based Tool"
    path = None
    runner = "directory"

    REQUIRED_PATHS = [
        str((Path(find_executable("reprounzip")) / ".." / "..").resolve()),
        tempfile.gettempdir(),
    ]

    def __init__(self):
        self.reprounzip = find_executable("reprounzip")
        self.dir = f"{tempfile.gettempdir()}/reprounzip-{uuid4()}"
        self.base_command = [self.reprounzip, self.runner]

    def setup(self):
        silent_run(self.base_command + ["setup", self.path, self.dir])

    def cmdline(self, context):
        return self.base_command + ["run", self.dir]

    def teardown(self):
        silent_run(self.base_command + ["destroy", self.dir])
