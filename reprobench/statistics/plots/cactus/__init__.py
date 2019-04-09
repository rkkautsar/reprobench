import os

from reprobench.statistics.plots.base import NotebookExecutor

DIR = os.path.dirname(__file__)


class CactusPlot(NotebookExecutor):
    DEFAULT_OUTPUT = "output/statistics/cactus.ipynb"
    INPUT_NOTEBOOK = os.path.join(DIR, "template.ipynb")
