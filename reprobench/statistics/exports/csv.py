from .base import PandasExporter


class CSVExport(PandasExporter):
    DEFAULT_OUTPUT = "output/statistics/benchmark.csv"

    @classmethod
    def save_df(cls, df, output):
        df.to_csv(output)
