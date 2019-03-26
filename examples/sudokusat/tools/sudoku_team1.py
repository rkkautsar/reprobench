import os
import subprocess
from reprobench.tools.executable import ExecutableTool
from reprobench.core.db import Parameter
from reprobench.utils import silent_run


class Team1SudokuSolver(ExecutableTool):
    name = "Team 1 Sudoku Solver"
    path = os.path.join(os.path.dirname(__file__), "sudoku_team1")

    @classmethod
    def cmdline(cls, context):
        task = os.path.abspath(context["run"]["task"])
        parameters = context["run"]["parameters"]
        solver_parameter = [p for p in parameters if p["key"] == "solver"]

        if len(solver_parameter) == 0:
            solver = "glucose"
        else:
            solver = solver_parameter[0]["value"]

        return [cls.path, f"-s={solver}", task]
