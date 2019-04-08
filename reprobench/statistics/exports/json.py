from .base import PandasExporter


class JSONExport(PandasExporter):
    DEFAULT_OUTPUT = "output/statistics/benchmark.json"

    @classmethod
    def save_df(cls, df, output):
        df.to_json(output)
