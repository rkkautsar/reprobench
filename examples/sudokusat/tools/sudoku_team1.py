import os
import subprocess
from reprobench.tools.reprozip import ReprozipTool
from reprobench.utils import silent_run


class Team1SudokuSolver(ReprozipTool):
    name = "Team 1 Sudoku Solver"
    path = os.path.join(os.path.dirname(__file__), "sudoku_team1.rpz")
    runner = "directory"

    def pre_run(self, context):
        task = context['task']
        assert task['type'] == 'file'
        silent_run(self.base_command + ["upload", self.dir, f"{task['path']}:input.txt"])

    def cmdline(self, context):
        parameters = context['parameter']
        solver = "riss"
        if "solver" in parameters:
            solver = parameters["solver"]
        
        return self.base_command + ["run", self.dir, f"run_{solver}"]
