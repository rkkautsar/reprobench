import itertools
import os
import subprocess
from pathlib import Path

from reprobench.tools.executable import ExecutableTool
from reprobench.utils import download_file


DIR = os.path.dirname(__file__)


class Lingeling(ExecutableTool):
    name = "Lingeling SAT solver"
    base_path = Path(DIR) / "_downloaded"
    path = base_path / "lingeling-master" / "plingeling"
    url = "https://github.com/arminbiere/lingeling/archive/master.zip"
    prefix = "-"

    def get_arguments(self):
        return itertools.chain.from_iterable(
            (f"-{key}", value) for key, value in self.parameters.items()
        )

    @classmethod
    def version(cls):
        out = subprocess.check_output([cls.path.with_name("lingeling"), "--version"])
        return out.strip().decode()

    @classmethod
    def setup(cls):
        cls.base_path.mkdir(parents=True, exist_ok=True)
        archive_path = cls.base_path / "lingeling.zip"
        download_file(cls.url, archive_path)
        subprocess.run(["unzip", archive_path], cwd=cls.base_path)
        make_path = cls.base_path / "lingeling-master"
        subprocess.run(["./configure.sh"], cwd=make_path, shell=True)
        subprocess.run(["make"], cwd=make_path, shell=True)

    @classmethod
    def is_ready(cls):
        return Path(cls.path).is_file()
