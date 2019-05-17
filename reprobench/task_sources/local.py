from pathspec import PathSpec
from pathlib import Path
from .base import BaseTaskSource


class LocalSource(BaseTaskSource):
    TYPE = "local"

    def __init__(self, path=None, patterns="", **kwargs):
        super().__init__(path)
        self.patterns = patterns

    def setup(self):
        spec = PathSpec.from_lines("gitwildmatch", self.patterns.splitlines())
        matches = spec.match_tree(self.path)
        return map(lambda match: Path(self.path).resolve() / match, matches)
