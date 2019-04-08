from pathlib import Path

import pandas as pd

from reprobench.core.base import Step
from reprobench.core.db import Run, db
from reprobench.utils import import_class


class PandasExporter(Step):
    DEFAULT_OUTPUT = None

    @classmethod
    def get_dataframe(cls, joins):
        query = Run.select().where(Run.status == Run.DONE)

        for model_class in joins:
            model = import_class(model_class)
            query = query.join_from(Run, model).select_extend(
                *model._meta.fields.values()
            )

        sql, params = query.sql()

        return pd.read_sql_query(sql, db, params=params)

    @classmethod
    def save_df(cls, df, output):
        raise NotImplementedError

    @classmethod
    def execute(cls, context, config=None):
        if config is None:
            config = {}

        joins = config.get("joins", [])
        output_dir = context.get("output_dir", None)
        output = Path(output_dir) / config.get("output", cls.DEFAULT_OUTPUT)
        output.parent.mkdir(parents=True, exist_ok=True)

        df = cls.get_dataframe(joins)
        # remove duplicated columns
        df = df.loc[:, ~df.columns.duplicated()]

        cls.save_df(df, output)
