import pandas as pd
import plotly.express as px
from plotly.graph_objs import Figure

from chat2plot.schema import AggregationType, AxisOrder, ChartType, Filter, PlotConfig
from chat2plot.transform import transform


def draw_plotly(df: pd.DataFrame, config: PlotConfig) -> Figure:
    df_filtered = filter_data(df, config.filters).copy()
    df_filtered = transform(df, config)

    chart_type = config.chart_type

    if chart_type in [ChartType.BAR, ChartType.HORIZONTAL_BAR]:
        agg = groupby_agg(df_filtered, config)
        x = agg.columns[0]
        y = agg.columns[-1]
        orientation = "v"

        if chart_type == ChartType.HORIZONTAL_BAR:
            x, y = y, x
            orientation = "h"

        fig = px.bar(
            agg,
            x=x,
            y=y,
            color=config.hue.column if config.hue else None,
            orientation=orientation,
        )
    elif chart_type == ChartType.SCATTER:
        fig = px.scatter(
            df_filtered,
            x=config.measures[0].column,
            y=config.measures[1].column,
            color=config.hue.column if config.hue else None,
        )
    elif chart_type == ChartType.PIE:
        agg = groupby_agg(df_filtered, config)
        fig = px.pie(agg, names=agg.columns[0], values=agg.columns[-1])
    elif chart_type in [ChartType.LINE, ChartType.AREA]:
        func_table = {ChartType.LINE: px.line, ChartType.AREA: px.area}

        if is_aggregation(config):
            agg = groupby_agg(df_filtered, config)
            fig = func_table[chart_type](agg, x=agg.columns[0], y=agg.columns[-1])
        else:
            assert config.dimension is not None
            fig = func_table[chart_type](
                df_filtered,
                x=config.dimension.column,
                y=config.measures[0].column,
                color=config.hue.column if config.hue else None,
            )
    else:
        raise ValueError(f"Unknown chart_type: {chart_type}")

    return fig


def groupby_agg(df: pd.DataFrame, config: PlotConfig) -> pd.DataFrame:
    assert len(config.measures) == 1

    group_by = [config.dimension.column] if config.dimension is not None else []

    if config.hue and config.hue != config.dimension:
        group_by.append(config.hue.column)

    agg_method = {
        AggregationType.AVG: "mean",
        AggregationType.SUM: "sum",
        AggregationType.COUNT: "count",
        AggregationType.DISTINCT_COUNT: "nunique",
        AggregationType.MIN: "min",
        AggregationType.MAX: "max",
    }

    m = config.measures[0]
    assert m.aggregation_method is not None

    if not group_by:
        return pd.DataFrame(
            {str(m): [df[m.column].agg(agg_method[m.aggregation_method])]}
        )
    else:
        agg = (
            df.groupby(group_by, dropna=False)[m.column]
            .agg(agg_method[m.aggregation_method])
            .rename(str(m))
        )
        if config.order_by == AxisOrder.NAME:
            agg = agg.sort_index()
        elif config.order_by == AxisOrder.VALUE:
            agg = agg.sort_values(ascending=False)

        return agg.reset_index()


def is_aggregation(config: PlotConfig) -> bool:
    return (
        len(config.measures) == 1 and config.measures[0].aggregation_method is not None
    )


def filter_data(df: pd.DataFrame, filters: list[Filter]) -> pd.DataFrame:
    if not filters:
        return df
    return df.query(" and ".join([f.query for f in filters]))