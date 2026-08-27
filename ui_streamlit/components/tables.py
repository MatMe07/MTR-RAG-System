"""Обёртка для таблиц (st.dataframe с fallback на st-aggrid)."""

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    HAS_AGGRID = True
except ImportError:
    HAS_AGGRID = False


def render_table(
    data,
    use_aggrid: bool = False,
    height: int = 400,
    selection_mode: str = "single",
    key: str = "table",
):
    """Рендер таблицы. При use_aggrid и доступности st-aggrid использует его."""
    if HAS_AGGRID and use_aggrid:
        return _render_aggrid(data, height, selection_mode, key)
    return _render_dataframe(data, height)


def _render_dataframe(data, height: int):
    if data is None or len(data) == 0:
        st.info("Нет данных.")
        return None
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, height=height)
    return df


def _render_aggrid(data, height: int, selection_mode: str, key: str):
    if data is None or len(data) == 0:
        st.info("Нет данных.")
        return None
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
    gb.configure_selection(selection_mode)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=False)
    gb.configure_side_bar()
    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        height=height,
        theme="streamlit",
        key=key,
        allow_unsafe_jscode=True,
    )
    return grid


def selected_rows(grid):
    """Извлекает выбранные строки из AgGrid-ответа."""
    if grid is None:
        return []
    selected = grid.get("selected_rows", [])
    if not selected:
        return []
    if isinstance(selected, pd.DataFrame):
        return selected.to_dict("records")
    return selected
