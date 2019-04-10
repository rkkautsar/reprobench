from reprobench.core.db import ParameterGroup, Run, db
from reprobench.executors.db import RunStatistic
from reprobench.utils import import_class

from .base import PandasExporter

try:
    import pandas as pd
except ImportError:
    pass


class RunTable(PandasExporter):
    @classmethod
    def get_dataframe(cls, config):
        joins = config.get("joins", [])
        query = Run.select()

        for model_class in joins:
            model = import_class(model_class)
            query = query.join_from(Run, model).select_extend(
                *model._meta.fields.values()
            )

        sql, params = query.sql()

        return pd.read_sql_query(sql, db, params=params)


class RunSummaryTable(PandasExporter):
    DEFAULT_COLUMNS = ("cpu_time", "wall_time", "max_memory")

    @classmethod
    def get_dataframe(cls, config):
        columns = config.get("columns", cls.DEFAULT_COLUMNS)
        tool_names = [
            f"{group.tool_id}_{group.name}" for group in ParameterGroup.select()
        ]
        multiindex = pd.MultiIndex.from_product((tool_names, columns))
        df = pd.DataFrame(index=multiindex).transpose()

        for group in ParameterGroup.select():
            tool_name = f"{group.tool_id}_{group.name}"
            query = (
                RunStatistic.select()
                .join(Run)
                .where(Run.tool_id == group.tool_id)
                .where(Run.parameter_group_id == group.id)
            )
            sql, params = query.sql()
            tool_df = pd.read_sql(sql, db, params=params)
            for col in columns:
                df.loc(axis=1)[tool_name, col] = tool_df[col]

        return df.describe()
