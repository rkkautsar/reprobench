from reprobench.core.base import Tool


class ExecutableTool(Tool):
    name = "Basic Executable Tool"
    path = None

    @classmethod
    def is_ready(cls):
        return True

