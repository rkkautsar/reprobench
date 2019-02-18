import subprocess
import functools
import operator

from reprobench.core.bases import Step
from reprobench.utils import find_executable, silent_run

# Not working yet
class IsolateExecutor(Step):
    def __init__(self):
        self.executable = find_executable("isolate")
    
    def run(self, context):
        tool = context['tool']
        tool.pre_run(context['task'], context['parameters'])

        output = subprocess.check_output(
        # print(
            [ self.executable, "--run", "-e" ] +
            functools.reduce(operator.iconcat, [ ["-d", f"{path}:rw"] for path in tool.REQUIRED_PATHS ]) +
            [ "--" ] +
            tool.cmdline(context['task'], context['parameters'])
        )
        return output
