from pathlib import Path

from reprobench.core.base import Step


class PandasExporter(Step):
    @classmethod
    def get_dataframe(cls, config):
        raise NotImplementedError

    @classmethod
    def save_df(cls, df, output):
        if output.endswith(".csv"):
            df.to_csv(output)
        elif output.endswith(".json"):
            df.to_json(output)
        else:
            raise NotImplementedError

    @classmethod
    def execute(cls, context, config=None):
        if config is None:
            config = {}

        output_dir = context.get("output_dir", None)
        output = Path(output_dir) / config.pop("output")
        output.parent.mkdir(parents=True, exist_ok=True)

        df = cls.get_dataframe(config)
        # remove duplicated columns
        df = df.loc[:, ~df.columns.duplicated()]

        cls.save_df(df, str(output))
