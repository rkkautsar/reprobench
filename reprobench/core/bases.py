class Runner:
    def __init__(self, config):
        pass

    def run(self):
        pass


class Step:
    @classmethod
    def register(cls, config={}):
        pass

    @classmethod
    def execute(cls, context, config={}):
        pass


class Tool:
    name = "Base Tool"
    REQUIRED_PATHS = []

    @classmethod
    def setup(cls):
        pass

    @classmethod
    def version(cls):
        return "1.0.0"

    @classmethod
    def pre_run(cls, context):
        pass

    @classmethod
    def cmdline(cls, context):
        pass

    @classmethod
    def post_run(cls, context):
        pass

    @classmethod
    def teardown(cls):
        pass
