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
        task = os.path.abspath(context["run"].task.path)
        parameters = context["run"].parameter_group.parameters

        solver_query = parameters.where(Parameter.key == "solver").first()
        if solver_query is None:
            solver = "glucose"
        else:
            solver = solver_query.value

        return [cls.path, f"-s={solver}", task]
