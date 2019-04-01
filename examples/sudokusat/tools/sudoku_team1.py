import os
import subprocess
from pathlib import Path

from reprobench.tools.executable import ExecutableTool
from reprobench.utils import download_file


DIR = os.path.dirname(__file__)


class Team1SudokuSolver(ExecutableTool):
    name = "Team 1 Sudoku Solver"
    base_path = Path(DIR) / "_downloaded"
    path = base_path / "sudoku-solver-master" / "solver"
    url = "https://github.com/rkkautsar/sudoku-solver/archive/master.zip"

    @classmethod
    def setup(cls):
        cls.base_path.mkdir(parents=True, exist_ok=True)
        zip_path = cls.base_path / "sudoku-solver.zip"
        download_file(cls.url, zip_path)
        subprocess.run(["unzip", str(zip_path)], cwd=cls.base_path)
        subprocess.run(["nim", "c", str(cls.path)])

    def get_arguments(self):
        solver = self.parameters.get("solver", "glucose")
        return [f"-s={solver}"]

    @classmethod
    def is_ready(cls):
        return Path(cls.path).is_file()
