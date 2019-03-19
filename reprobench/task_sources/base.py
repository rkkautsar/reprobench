class BaseTaskSource(object):
    def __init__(self, path=None, **kwargs):
        self.path = path

    def setup(self):
        return []
