class Runner:
    def __init__(self, config):
        pass

    def run(self):
        pass


class Step:
    @classmethod
    def register(cls):
        pass

    @classmethod
    def execute(cls, context):
        pass


class Tool:
    name = "Base Tool"
    REQUIRED_PATHS = []

    def setup(self):
        pass

    def version(self):
        return "1.0.0"

    def pre_run(self, context):
        pass

    def cmdline(self, context):
        pass

    def post_run(self, context):
        pass

    def teardown(self):
        pass
