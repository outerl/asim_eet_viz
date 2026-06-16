"""Module containing helper functions for the visualizer module."""

import logging
from pathlib import Path
from typing import Any, Optional, Callable

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots


logger = logging.getLogger(__name__)


def _normalize_column_selection(columns: Any) -> list[Any] | None:
    if columns is None:
        return None

    if isinstance(columns, (str, int)):
        return [columns]

    return list(columns)


def _resolve_input_path(base_dir: str | Path, file_name: str) -> Path:
    path = Path(base_dir) / file_name
    suffix = path.suffix.lower()

    if suffix in {".csv", ".parquet"}:
        return path

    for candidate in (path.with_suffix(".parquet"), path.with_suffix(".csv")):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Could not find '{file_name}' as either a parquet or csv file under '{base_dir}'."
    )


def read_input_table(base_dir: str | Path, file_name: str, **read_kwargs: Any) -> pd.DataFrame:
    """Read a notebook input table from parquet or csv using a csv-compatible API.

    If ``file_name`` has no extension, parquet is preferred when both parquet and csv
    versions exist.
    """

    path = _resolve_input_path(base_dir, file_name)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, **read_kwargs)

    parquet_kwargs = dict(read_kwargs)
    index_col = parquet_kwargs.pop("index_col", None)
    usecols = parquet_kwargs.pop("usecols", None)
    columns = parquet_kwargs.pop("columns", None)

    if usecols is not None and columns is not None and list(usecols) != list(columns):
        raise ValueError("Pass either matching 'usecols' and 'columns' values, or only one of them.")

    selected_columns = _normalize_column_selection(columns)
    if selected_columns is None:
        selected_columns = _normalize_column_selection(usecols)

    if selected_columns is not None and index_col is not None:
        index_columns = _normalize_column_selection(index_col)
        selected_columns = list(dict.fromkeys([*selected_columns, *index_columns]))

    if selected_columns is not None:
        parquet_kwargs["columns"] = selected_columns

    df = pd.read_parquet(path, **parquet_kwargs)
    if index_col is not None:
        df = df.set_index(index_col)

    return df


COLOR_MAP = {
    "Orange_light": "#FAC58F",
    "Marine_light": "#66A8C6",
    "Leaf_light": "#bdddbb",
    "Cherry_light": "#CE5964",
    "Grey_light": "#737380",
    "Orange": "#F68B1F",
    "Marine": "#006FA1",
    "Leaf": "#91C78E",
    "Cherry": "#BA1222",
    "Grey": "#48484A",
}

LABEL_COLORS = {
    "Changed": "Orange_light",
    "Unchanged": "Marine_light",
    "Newly Created": "Leaf_light",
    "Removed": "Cherry_light",
    "Increased": "Leaf",
    "Decreased": "Cherry",
    "Workplace moved into area": "Leaf_light",
    "Workplace moved out of area": "Cherry_light",
}

def create_bar_chart(
    source_data: pd.DataFrame,
    source: str,
    col: str,
    plot_col: str,
    **plot_kwargs,
) -> plotly.graph_objs.Figure:
    """
    Create a bar chart with unweighted and weighted values.

    Args:
        source_data (pd.DataFrame): The dataframe containing the data.
        source (str): The source name to be used as the data name
        col (str): The column name of the variable to plot.
        plot_col (str): The column name of values to plot.
        plot_kwargs: Additional keyword arguments to pass to the plot.

    Returns:
        plotly.graph_objs.Figure: Plotly figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=source_data[col],
            y=source_data[plot_col],
            name=source,
            marker_color=list(COLOR_MAP.values())[0],
            **plot_kwargs,
        ),
    )

    return fig


def create_pie_chart(
    df: pd.DataFrame,
    columns: list,
) -> plotly.graph_objs.Figure:
    """
    Create pie charts with unweighted data.

    Args:
        df (pd.DataFrame): The dataframe containing the data.
        columns (list): The columns to plot.

    Returns:
        plotly.graph_objs.Figure: Plotly figure.
    """

    # Initialize the subplot grid
    fig = go.Figure()

    # Loop through the columns
    for col, column in enumerate(columns, start=1):
        # build color pallette from labels, if available, otherwise go in order
        colors = [COLOR_MAP[LABEL_COLORS[df.index[idx]]] if df.index[idx] in LABEL_COLORS
                  else list(COLOR_MAP.values())[idx % len(COLOR_MAP)]
                  for idx in range(len(df.index))]
        
        pie = go.Pie(
                labels=df.index,
                values=df[column],
                textinfo="label+percent",
                hoverinfo='value',
                textposition="outside",
                automargin=True,
            )
        pie.marker.colors = colors
        fig.add_trace(pie)
    return fig


def monofilter(
    zone_set: str, affected_zones: list
) -> Callable:
    """
    Define filter functions corresponding to zone_set options

    Each filter will accept a Series with values of TAZ or MAZ ids
    and will return a Series with the same index reresenting whether
    the corresponding value is in the selected zone set.
    """

    # for all zones
    def allow_all(zone_series: pd.Series) -> pd.Series:
        return pd.Series(True, zone_series.index)

    # only zones inside the affected area
    def allow_affected_zones(zone_series: pd.Series) -> pd.Series:
        return zone_series.isin(affected_zones)


    # select the corresponding filters based on zone_set parameter
    match zone_set:
        case "all":
            return allow_all
        case "affected":
            return allow_affected_zones
        case _:
            raise f"Unknown zone set: {zone_set}. Acceptable options: 'all','affected'"


def multifilter(how: str, filterfunc: Callable) -> Callable:
    """
    A method to easily combine multiple zone matches, either requiring all
    or any element to match the filter for the result to be valid. This is
    commonly used to define whether a filter must be matching for EITHER or 
    BOTH the origin and/or the destination of a tour or trip.

    Parameters:
        how: str                Acceptable inputs: "all" or "any"
        filterfunc: Callable    function which accepts as input a Series of zones
                                and returns whether or not they are in the filtered
                                area, as a Series of booleans, i.e. the signature:

                                   def filterfunc(
                                        in_series: Series[int]   # zone (TAZ/MAZ) ID values
                                   ) -> Series[bool]:
                                   
                                   # where in_series.index == filterfunc(in_series).index

    Returns
        a function which accepts a list of Series of booleans and returns a combined
        series according to the "how" parameter, i.e. one with the signature:

        def multifilterfunc(
            series_list:    list[Series[int]]   # a list of Series of zone ID values for input
                                                # into the underlying filterfunc

        ) -> Series[bool]   # whether the input index is accepted by the combined filters

    """
    if how == 'all': # equivalent to AND
        return lambda series: pd.concat([filterfunc(x) for x in series], axis=1).all(axis=1)
    
    elif how == 'any': # equivalent to OR
        return lambda series: pd.concat([filterfunc(x) for x in series], axis=1).any(axis=1)
    
    else:
        # I don't think there's any need for an XOR, and that isn't straightforward with an
        # arbitrary number of series (order matters)
        raise NotImplementedError(f"Unknown how method: {how}")
    

def get_filters(zone_set:str, how:str, affected_zones: list)->tuple[Callable,Callable]:
    """
    A method that returns the appropriate filters for creating affected-area filters.

    This method creates two function objects - one for filtering a single vector of
    zone IDs, and one for filtering multiple vectors. The latter has the former filter
    as its underlying filter, and the individual vectors are passed to it individually
    before they are combined together using the strategy defined by the `how` parameter.
    
    The `zone_set` parameter is defined as one of the following options:

        - "all"         the returned filters will include all input records regardless
                        of the set of zones defined in the `affected_zones` list

        - "affected"    the returned filters will include only the records whose zone
                        IDs are included in the `affected_zones` list of IDs

        - "unaffected"  the returned filters will include only the records whose zone
                        IDs are NOT included in the `affected_zones` list of IDs
    
    The `how` parameter is defined as one of the following options:

        - "all"         the records which are included by the multifilter are those
                        for which ALL of the input series are included by the underlying
                        filter function

        - "any"         the records which are included by the multifilter are those
                        for which ANY of the input series are included by the underlying
                        filter function

    The `affected_zones` parameter is a list of zone IDs which define the "affected area"
    of a study scenario. This list will be used to filter the Series input into the 
    returned filters, unless the `zone_set` parameter is set to "all".

    The returned tuple is of the format `(monofilter, multifilter)`, where the monofilter
    accepts a single Series as input and the multifilter accepts a list of Series as input

    """

    assert zone_set in ["all","affected","unaffected"], f"""Unknown `zone_set` parameter: {zone_set}. 
    Allowed options are 'all', 'affected', and 'unaffected'"""

    if zone_set == "all":
        # this filter is actually a non-filter
        single_filter: Callable = monofilter('all', affected_zones)

    else:
        # these are actually filters using the affected_zones list
        single_filter: Callable = monofilter('affected', affected_zones)
    
    # construct the multifilter using the newly created monofilter
    multi_filter: Callable = multifilter(how, single_filter)
   
   # if we actually want the NEGATION of the affected area
    if zone_set == "unaffected":

        # define the corresponding unaffected-area filters
        def unaffected_single(x: pd.Series) -> pd.Series:
            return ~single_filter(x)

        def unaffected_multi(xs: pd.Series) -> pd.Series:
            return ~multi_filter(xs)
        
        return unaffected_single, unaffected_multi
    
    # otherwise return the original filters
    else:
        return single_filter, multi_filter
    
def get_time_period_index(
    bin: int,
    time_period_mapping: Optional[list] = [0,6,12,25,32,48],
) -> int:
    """
    Convert a bin number to a time period index.

    Args:
        bin (int): The bin number.
        time_period_mapping (list, optional): A mapping of bin numbers to time periods. Defaults to None.

    Returns:
        int: The time period index.
    """

    for i, period in enumerate(time_period_mapping):
        if bin-1 < period:
            return i - 1
    return len(time_period_mapping) - 1