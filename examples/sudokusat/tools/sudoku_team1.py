import os
import subprocess
from reprobench.tools.executable import ExecutableTool
from reprobench.core.db import Parameter
from reprobench.utils import silent_run


class Team1SudokuSolver(ExecutableTool):
    name = "Team 1 Sudoku Solver"
    path = os.path.join(os.path.dirname(__file__), "sudoku_team1")
