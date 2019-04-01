import os
import subprocess
from pathlib import Path

from reprobench.tools.executable import ExecutableTool
from reprobench.utils import download_file


DIR = os.path.dirname(__file__)


class Glucose(ExecutableTool):
    name = "Glucose SAT solver"
    base_path = Path(DIR) / "_downloaded"
    path = base_path / "glucose-syrup-4.1" / "parallel" / "glucose-syrup"
    url = "http://www.labri.fr/perso/lsimon/downloads/softwares/glucose-syrup-4.1.tgz"
    prefix = "-"

    @classmethod
    def version(cls):
        return "4.1"

    @classmethod
    def setup(cls):
        cls.base_path.mkdir(parents=True, exist_ok=True)
        archive_path = cls.base_path / "glucose-syrup-4.1.tgz"
        download_file(cls.url, archive_path)
        subprocess.run(["tar", "xf", archive_path], cwd=cls.base_path)
        make_path = cls.base_path / "glucose-syrup-4.1" / "parallel"
        subprocess.run(["make"], cwd=make_path, shell=True)

    @classmethod
    def is_ready(cls):
        return Path(cls.path).is_file()
